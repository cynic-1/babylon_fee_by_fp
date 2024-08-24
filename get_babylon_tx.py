import requests
import json
import time
import os
from requests.exceptions import RequestException

RPC_URL = ""
BLOCKS_FILE = "downloaded_blocks.json"


def rpc_call(method, params=[], max_retries=3):
    headers = {'content-type': 'application/json'}
    payload = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": method,
        "params": params
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(RPC_URL, json=payload, headers=headers)
            result = response.json()
            if result['error'] is not None:
                print(f"RPC error: {result['error']}")
                if attempt < max_retries - 1:
                    print(f"Retrying in 5 seconds... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(5)
                continue
            return result['result']
        except RequestException as e:
            print(f"Request failed: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in 5 seconds... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(5)

    print("Failed after max retries.")
    return None


def download_blocks(start_height, end_height):
    if os.path.exists(BLOCKS_FILE):
        print(f"Loading blocks from {BLOCKS_FILE}")
        with open(BLOCKS_FILE, 'r') as f:
            return json.load(f)

    blocks = []
    for height in range(start_height, end_height + 1):
        print(f"Downloading block at height {height}")
        block_hash = rpc_call("getblockhash", [height])
        if block_hash is None:
            print(f"Failed to get block hash for height {height}")
            continue
        block = rpc_call("getblock", [block_hash, 2])
        if block is None:
            print(f"Failed to get block data for height {height}")
            continue
        blocks.append(block)
        time.sleep(1)  # Add a delay to avoid rate limiting

    print(f"Saving blocks to {BLOCKS_FILE}")
    with open(BLOCKS_FILE, 'w') as f:
        json.dump(blocks, f)

    return blocks


def parse_op_return(hex_data):
    if not hex_data.startswith('6a47'):
        return None

    data = hex_data[4:]  # Remove '6a47'
    if len(data) < 142:  # 4 + 1 + 32 + 32 + 2 = 71 bytes * 2 (hex)
        return None

    return {
        'magic_bytes': data[:8],
        'version': data[8:10],
        'staker_public_key': data[10:74],
        'fp_public_key': data[74:138],
        'staking_time': data[138:142]
    }


def get_input_value(txid, vout):
    # This function will need to make an RPC call to get the value of the input
    # We'll use a cache to avoid repeated calls for the same input
    cache_key = f"{txid}:{vout}"
    if cache_key in get_input_value.cache:
        return get_input_value.cache[cache_key]

    tx = rpc_call("getrawtransaction", [txid, True])
    if tx and 'vout' in tx and len(tx['vout']) > vout:
        value = tx['vout'][vout]['value']
        get_input_value.cache[cache_key] = value
        return value
    return 0


# Initialize the cache
get_input_value.cache = {}


def process_transactions(blocks):
    grouped_transactions = {}

    for block in blocks:
        # Skip the first transaction (coinbase) in each block
        for tx in block['tx'][1:]:
            print(f"Processing transaction: {tx['txid']}")
            op_return_output = None
            total_output = 0
            for vout in tx['vout']:
                if 'scriptPubKey' in vout and 'asm' in vout['scriptPubKey'] and vout['scriptPubKey']['asm'].startswith(
                        'OP_RETURN'):
                    op_return_output = vout['scriptPubKey']['hex']
                total_output += vout['value']

            if op_return_output:
                # Calculate total input
                total_input = sum(get_input_value(vin['txid'], vin['vout']) for vin in tx['vin'])

                # Calculate fee
                fee = total_input - total_output if total_input > total_output else 0

                parsed_op_return = parse_op_return(op_return_output)

                if parsed_op_return:
                    staker_public_key = parsed_op_return['staker_public_key']
                    if staker_public_key not in grouped_transactions:
                        grouped_transactions[staker_public_key] = []

                    grouped_transactions[staker_public_key].append({
                        'txid': tx['txid'],
                        'total_input': total_input,
                        'total_output': total_output,
                        'fee': fee,
                        'op_return': parsed_op_return
                    })

    return grouped_transactions

def main():
    start_height = 857910
    end_height = 857916

    blocks = download_blocks(start_height, end_height)
    grouped_transactions = process_transactions(blocks)

    with open('grouped_transactions.json', 'w') as f:
        json.dump(grouped_transactions, f, indent=2)

    print("Data has been saved to grouped_transactions.json")


if __name__ == "__main__":
    main()
