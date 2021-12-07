# 発着駅制約を生成するスクリプト
import pandas as pd
from typing import NamedTuple

# 定数
METRO_HATSUNORI = 60
METRO_SETSUZOKU = 190
TOEI_HATSUNORI = 40
TOEI_SETSUZOKU = 150


class Dist(NamedTuple):
    hatsunori: int
    setsuzoku: int


class Constr(NamedTuple):
    sta: list
    start: dict[str:bool]
    goal: dict[str:bool]


class Route:
    def __init__(self, d: Dist, sta: pd.DataFrame, mat: pd.DataFrame):
        self.hatsunori: int = d.hatsunori
        self.setsuzoku: int = d.setsuzoku
        self.sta: list[str] = list(sta.index)
        self.connect: list[str] = list(sta.query("connect == True").index)
        self.change: list[str] = list(sta.query("change == True").index)
        self.matrix: pd.DataFrame = mat


def make_constr(f: Route, s: Route, mode: str, con: str = "") -> Constr:
    # mode:f or d or sta_name
    if mode == "f":
        # 先行ケース
        # 発駅:すべての乗換駅に接続以内、すべての後続乗換駅に初乗り以内、乗換駅との距離が0でない
        # 着駅:乗換駅との距離が0でないすべての接続駅
        sta = f.sta
        is_start: dict[str:bool] = {i: False for i in f.sta}
        is_goal: dict[str:bool] = {i: False for i in f.sta}
        con_change_set: dict[str:set] = {i: set() for i in f.connect}  # 接続駅から初乗り以内の後続乗換駅セット
        for i in con_change_set:
            for j in s.change:
                if 0 < s.matrix[i][j] <= s.hatsunori:
                    con_change_set[i].add(j)

        for i in is_start:
            a = []
            n = []
            for j in f.change:
                if i in f.connect and f.matrix[i][j] == 0:
                    n.append(i)
                if 0 < f.matrix[i][j] <= f.setsuzoku:
                    a.append(j)
            change = False
            if len(a) == len(f.change):
                change = True
            del a
            a = set()
            for j in f.connect:
                if 0 < f.matrix[i][j] <= f.hatsunori:
                    a = a | con_change_set[j]
            con = False
            if len(a) == len(s.change):
                con = True
            if change and con and i not in f.change and i not in f.connect:
                is_start[i] = True
            if i in f.connect and i not in n:
                is_goal[i] = True

    elif mode == "d":
        # ダミーケース
        # 発駅:乗換駅でないすべての接続駅
        # 着駅:いずれかの接続駅から初乗り以内かつ乗換駅でないすべての駅
        sta = s.sta
        is_start: dict[str:bool] = {i: False for i in sta}
        is_goal: dict[str:bool] = {i: False for i in sta}
        for i in s.connect:
            for j in s.change:
                if s.matrix[i][j] == 0:
                    continue
                is_start[i] = True
        for i in sta:
            for j in s.connect:
                if 0 < s.matrix[i][j] <= s.hatsunori and i not in s.change and i not in s.connect:
                    is_goal[i] = True

    else:
        # 後続ケース
        # 発駅:conで指定された駅
        # 着駅:指定された発駅から初乗り以内
        sta = s.sta
        is_start = {i: True if i == con else False for i in sta}
        is_goal = {i: False for i in sta}
        con_hatsunori = []  # 指定駅から初乗り以内の接続駅
        for i in s.connect:
            if 0 < s.matrix[i][mode] <= f.hatsunori:
                con_hatsunori.append(i)
        for i in sta:
            if i in s.connect or i in s.change:
                continue
            for j in con_hatsunori:
                if s.matrix[i][j] <= s.hatsunori:
                    is_goal[i] = True

    return Constr(sta=sta, start=is_start, goal=is_goal)


def out(constr: Constr, path: str) -> None:
    a = "sta,start,goal\n"
    for i in constr.sta:
        a += f"{i},{constr.start[i]},{constr.goal[i]}\n"
    with open(path, mode="w", encoding="utf8") as f:
        f.write(a)


def main() -> None:
    fd = Dist(TOEI_HATSUNORI, TOEI_SETSUZOKU)
    f = Route(fd, pd.read_csv("./resources/toei/sta.csv", index_col=0), pd.read_csv("./resources/toei/matrix.csv",
                                                                                    index_col=0))
    sd = Dist(METRO_HATSUNORI, METRO_SETSUZOKU)
    s = Route(sd, pd.read_csv("./resources/metro/sta.csv", index_col=0), pd.read_csv("./resources/metro/matrix.csv",
                                                                                     index_col=0))
    a = make_constr(f, s, "f")
    for i in a.sta:
        print(i, a.start[i], a.goal[i])
    out(a, "./resources/toei/constr.csv")


if __name__ == "__main__":
    main()
