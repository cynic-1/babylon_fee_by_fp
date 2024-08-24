import json
from collections import defaultdict

def load_and_process_data():
    # 读取JSON文件
    with open('grouped_transactions.json', 'r') as f:
        data = json.load(f)

    # 创建一个默认字典来存储分组后的数据
    grouped_by_fp = defaultdict(lambda: {'transaction_count': 0, 'total_fee': 0})

    # 遍历数据并进行分组
    for staker_public_key, transactions in data.items():
        for tx in transactions:
            fp_public_key = tx['op_return'].get('fp_public_key')
            if fp_public_key:
                grouped_by_fp[fp_public_key]['transaction_count'] += 1
                grouped_by_fp[fp_public_key]['total_fee'] += tx['fee']

    # 将defaultdict转换为普通字典
    return dict(grouped_by_fp)

def sort_by_fee(grouped_data):
    # 将字典转换为列表并按total_fee排序
    sorted_data = sorted(grouped_data.items(), key=lambda x: x[1]['total_fee'], reverse=True)
    return sorted_data

def main():
    grouped_data = load_and_process_data()
    sorted_data = sort_by_fee(grouped_data)

    # 打印结果
    print("分组结果（按手续费降序排列）：")
    for fp_public_key, stats in sorted_data:
        print(f"FP Public Key: {fp_public_key}")
        print(f"  交易总量: {stats['transaction_count']}")
        print(f"  Fee总量: {stats['total_fee']}")
        print()

    # 将排序后的结果转换回字典
    sorted_dict = {k: v for k, v in sorted_data}

    # 将结果保存到新的JSON文件
    with open('grouped_by_fp_sorted.json', 'w') as f:
        json.dump(sorted_dict, f, indent=2)

    print("排序后的分组结果已保存到 grouped_by_fp_sorted.json 文件中。")

if __name__ == "__main__":
    main()
