import csv
import operator


# sort_rowで指定した列を並び替える関数
def sort_csv(csv_file, sort_row, desc):
    '''
    第一引数：編集するCSVファイルをフルパスで指定
    第二引数：ソートする列を数字で指定(左から0,1,2・・・)
    第三引数：昇順(False)降順(True)を指定
    '''
    csv_data = csv.reader(open(csv_file), delimiter=',')
    header = next(csv_data)
    sort_result = sorted(csv_data, reverse=desc,
                         key=operator.itemgetter(sort_row))

    with open(csv_file, "w") as f:
        data = csv.writer(f, delimiter=',')
        data.writerow(header)
        for r in sort_result:
            data.writerow(r)
        print("done")
