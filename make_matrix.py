import pandas as pd


def make_matrix(edges: pd.DataFrame, sta: pd.DataFrame) -> dict[str:dict[str:int]]:
    sta_list: list[str] = list(sta.index)
    matrix: dict[str:dict[str:int]] = {i: {j: 0 if i == j else 10000 for j in sta_list} for i in sta_list}
    for i in edges.itertuples():
        matrix[i.dep][i.arr] = i.dist
        matrix[i.arr][i.dep] = i.dist
    for k in sta_list:
        for i in sta_list:
            for j in sta_list:
                matrix[i][j] = min(matrix[i][j], matrix[i][k] + matrix[k][j])
    return matrix


def out_matrix(matrix: dict[str:dict[str:int]], path: str) -> None:
    a: str = ","
    for i in matrix:
        a += i + ","
    a = a.rstrip(",") + "\n"
    for i in matrix:
        a += i + ","
        for j in matrix[i]:
            a += f"{matrix[i][j]},"
        a = a.rstrip(",") + "\n"
    with open(path, mode="w", encoding="utf8") as f:
        f.write(a)


def main() -> None:
    edges = pd.read_csv("./resources/metro/edges.csv")
    sta = pd.read_csv("./resources/metro/sta.csv", index_col=0)
    out = "./resources/metro/matrix.csv"
    matrix = make_matrix(edges, sta)
    out_matrix(matrix, out)


if __name__ == "__main__":
    main()
