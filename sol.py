import json
from typing import NamedTuple
import mip
import pandas as pd


class FilePath(NamedTuple):
    edges: str
    constr: str
    change: str


class Edges:
    def __init__(self, e_df: pd.DataFrame, m: mip.Model, change: list[list[list[str, str]]]):
        self.edges: list[mip.Var] = []
        self.line: list[str] = list(e_df["line"])
        self.dist: list[int] = list(e_df["dist"])
        self.__edges_sta_set: list[set] = []
        self.__sta_edge_dict: dict[tuple[str, str]:int] = dict()
        for i in e_df.itertuples():
            self.edges.append(m.add_var(f"({i.dep}-{i.arr})", 0, 1, var_type="B"))
            self.__edges_sta_set.append({i.dep, i.arr})
            self.__sta_edge_dict[i.dep, i.arr] = i.Index
            self.__sta_edge_dict[i.dep, i.arr] = i.Index
        # 乗換強制
        for i in change:
            a = []
            for j in i:
                a.append(self.__sta_edge_dict[j[0], j[1]])
            m += mip.xsum(self.edges[k] for k in a) == 1

    def get_edge_num(self, dep: str, arr: str) -> int:
        return self.__sta_edge_dict[dep, arr]

    def get_edge(self, dep: str, arr: str) -> mip.Var:
        return self.edges[self.get_edge_num(dep, arr)]

    def get_other_sta(self, e_num: int, sta: str) -> str:
        a = self.__edges_sta_set[e_num] - {sta}
        return list(a)[0]

    def get_sta(self, n: int) -> tuple[str, str]:
        return tuple(self.__edges_sta_set[n])


class Sta:
    def __init__(self, name: str, e_list: list[int], edges: Edges, m: mip.Model):
        self.__model: mip.Model = m
        self.start: mip.Var = m.add_var(f"(始-{name})", 0, 1, var_type="B")
        self.goal: mip.Var = m.add_var(f"(終-{name})", 0, 1, var_type="B")
        self.edge_list: list[int] = e_list
        m += mip.xsum(edges.edges[i] for i in e_list) + self.start + self.goal <= 2
        for i in e_list:
            m += mip.xsum(edges.edges[j] for j in e_list) + self.start + self.goal >= 2 * edges.edges[i]

    def set_start(self, b: bool) -> None:
        if b:
            self.__model += self.start == 1
        else:
            self.__model += self.start == 0

    def set_goal(self, b: bool) -> None:
        if b:
            self.__model += self.goal == 1
        else:
            self.__model += self.goal == 0


class ModelReturn(NamedTuple):
    model: mip.Model
    edges: Edges
    sta: dict[str: Sta]


def make_model(path: FilePath) -> ModelReturn:
    edges_csv = pd.read_csv(path.edges)
    constr_csv = pd.read_csv(path.constr, index_col=0)
    with open(path.change, mode="r", encoding="utf8") as f:
        change = json.load(f)

    # 問題を宣言
    m: mip.Model = mip.Model()
    edges: Edges = Edges(edges_csv, m, change)
    se = {i: [] for i in constr_csv.index}
    for i in edges_csv.itertuples():
        se[i.dep].append(i.Index)
        se[i.arr].append(i.Index)
    sta: dict[str: Sta] = {i: Sta(i, se[i], edges, m) for i in constr_csv.index}
    # 制約式ファイルから発着駅を強制
    for i in constr_csv.itertuples():
        if not i.start:
            sta[i.Index].set_start(False)
        if not i.goal:
            sta[i.Index].set_goal(False)
    # 発着駅は各々一つですよ制約
    m += mip.xsum(sta[i].start for i in sta) == 1
    m += mip.xsum(sta[i].goal for i in sta) == 1
    return ModelReturn(m, edges, sta)


def loop_chk(m: ModelReturn) -> int:  # 問題はOPTIMALであると仮定する(これを呼ぶ前に確認せよ

    if m.model.status != mip.OptimizationStatus.OPTIMAL:
        print("問題が解けてません")
        return -1

    # まず起終点を探す
    route: list[int] = []
    start: str = ""
    goal: str = ""
    for i in m.sta:
        if m.sta[i].start.x == 1:
            start: str = i
            for j in m.sta[i].edge_list:
                if m.edges.edges[j].x == 1:
                    route.append(j)
        if m.sta[i].goal.x == 1:
            goal: str = i

    # ルートを記述する
    temp = start
    while True:
        if len(route) == 0:  # ルートがなかったら終わり
            break
        print(temp)
        print(m.edges.line[route[-1]])
        temp = m.edges.get_other_sta(route[-1], temp)  # 次の駅を決める
        if temp == goal:  # 終点駅についたら終わり
            print(temp)
            break
        for i in m.sta[temp].edge_list:
            if m.edges.edges[i].x == 1 and i not in route:
                route.append(i)
                break

    # 値が1でrouteに含まれない枝を探す
    not_route: list[int] = []
    for i, e in enumerate(m.edges.edges):
        if e.x == 1 and i not in route:
            not_route.append(i)
    if len(not_route) == 0:  # ループがなくなったら終わり
        print("No Loop")
        return 0
    while len(not_route) > 0:  # どんどんlistを空になるまで消してく
        loop: list[int] = [not_route.pop()]
        l_start, l_goal = m.edges.get_sta(loop[-1])
        temp = l_start
        while True:
            if temp == l_goal:
                break
            for i in m.sta[temp].edge_list:
                if m.edges.edges[i].x == 1 and i not in loop:
                    loop.append(i)
                    not_route.remove(i)
                    break
            temp = m.edges.get_other_sta(loop[-1], temp)
        m.model += mip.xsum(m.edges.edges[i] for i in loop) <= len(loop) - 1

    # ここまで行くならループがあったことになる
    print("Loop Find")
    return 1  # modelは参照渡しなのでな


def main() -> None:
    pass


if __name__ == "__main__":
    main()
