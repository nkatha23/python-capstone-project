from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
import os

# Node access params
RPC_URL = "http://alice:password@127.0.0.1:18443"

def main():
    try:
        # General client for non-wallet-specific commands
        client = AuthServiceProxy(RPC_URL)

        # Get blockchain info
        blockchain_info = client.getblockchaininfo()
        print("Blockchain Info:", blockchain_info)

        # Create/Load the wallets, named 'Miner' and 'Trader'
        wallets = ['Miner', 'Trader']
        
        for wallet_name in wallets:
            try:
                # Try to load the wallet first
                client.loadwallet(wallet_name)
                print(f"Loaded existing wallet: {wallet_name}")
            except JSONRPCException as e:
                if "not found" in str(e) or "does not exist" in str(e):
                    try:
                        # Create the wallet if it doesn't exist
                        client.createwallet(wallet_name)
                        print(f"Created new wallet: {wallet_name}")
                    except JSONRPCException as create_error:
                        print(f"Error creating wallet {wallet_name}: {create_error}")
                        return
                elif "already loaded" in str(e):
                    print(f"Wallet {wallet_name} is already loaded")
                else:
                    print(f"Error loading wallet {wallet_name}: {e}")
                    return

        # Create wallet-specific clients
        miner_client = AuthServiceProxy(f"{RPC_URL}/wallet/Miner")
        trader_client = AuthServiceProxy(f"{RPC_URL}/wallet/Trader")

        # Generate spendable balances in the Miner wallet
        # In regtest, coinbase outputs mature after 100 blocks
        current_height = blockchain_info['blocks']
        print(f"Current block height: {current_height}")
        
        # Check current balance
        miner_balance = miner_client.getbalance()
        print(f"Miner current balance: {miner_balance} BTC")
        
        # Generate address for mining rewards
        miner_address = miner_client.getnewaddress("mining", "bech32")
        print(f"Miner address: {miner_address}")
        
        # Mine blocks to get spendable balance (need at least 101 blocks total for first coinbase to mature)
        blocks_needed = max(0, 101 - current_height)
        if miner_balance < 25:  # Need at least 25 BTC to send 20
            blocks_needed = max(blocks_needed, 25)  # Mine at least 25 more blocks
        
        if blocks_needed > 0:
            print(f"Mining {blocks_needed} blocks to generate spendable balance...")
            block_hashes = client.generatetoaddress(blocks_needed, miner_address)
            print(f"Mined {len(block_hashes)} blocks")
        
        # Check balance after mining
        miner_balance = miner_client.getbalance()
        print(f"Miner balance after mining: {miner_balance} BTC")

        # Load the Trader wallet and generate a new address
        trader_address = trader_client.getnewaddress("receiving", "bech32")
        print(f"Trader receiving address: {trader_address}")

        # Send 20 BTC from Miner to Trader
        send_amount = 20.0
        print(f"Sending {send_amount} BTC from Miner to Trader...")
        
        tx_id = miner_client.sendtoaddress(trader_address, send_amount)
        print(f"Transaction ID: {tx_id}")

        # Check the transaction in the mempool
        mempool_info = client.getmempoolinfo()
        print(f"Mempool info: {mempool_info}")
        
        mempool_txs = client.getrawmempool()
        print(f"Transactions in mempool: {len(mempool_txs)}")
        
        if tx_id in mempool_txs:
            print(f"Transaction {tx_id} found in mempool")
            
            # Get transaction details from mempool
            tx_details = client.getrawtransaction(tx_id, True)
            print(f"Transaction details: {tx_details}")

        # Mine 1 block to confirm the transaction
        print("Mining 1 block to confirm transaction...")
        new_block_hash = client.generatetoaddress(1, miner_address)[0]
        print(f"Mined block: {new_block_hash}")
        
        # Verify transaction is confirmed
        confirmed_tx = client.gettransaction(tx_id)
        print(f"Transaction confirmations: {confirmed_tx['confirmations']}")

        # Extract all required transaction details
        tx_raw = client.getrawtransaction(tx_id, True)
        block_info = client.getblock(new_block_hash)
        
        # Get wallet transaction details
        miner_tx_details = miner_client.gettransaction(tx_id)
        
        # Prepare output data
        output_data = {
            'transaction_id': tx_id,
            'block_hash': new_block_hash,
            'block_height': block_info['height'],
            'sender_wallet': 'Miner',
            'receiver_wallet': 'Trader',
            'receiver_address': trader_address,
            'amount_sent': send_amount,
            'transaction_fee': abs(miner_tx_details['fee']) if 'fee' in miner_tx_details else 'N/A',
            'confirmations': confirmed_tx['confirmations'],
            'tx_size': tx_raw['size'],
            'tx_vsize': tx_raw['vsize'],
            'inputs': len(tx_raw['vin']),
            'outputs': len(tx_raw['vout']),
            'miner_balance_before': miner_balance - send_amount - abs(miner_tx_details.get('fee', 0)),
            'miner_balance_after': miner_client.getbalance(),
            'trader_balance_after': trader_client.getbalance()
        }

        # Write the data to ../out.txt in the specified format
        output_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_file = os.path.join(output_dir, 'out.txt')
        
        with open(output_file, 'w') as f:
            f.write("Bitcoin Transaction Details\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Transaction ID: {output_data['transaction_id']}\n")
            f.write(f"Block Hash: {output_data['block_hash']}\n")
            f.write(f"Block Height: {output_data['block_height']}\n")
            f.write(f"Sender Wallet: {output_data['sender_wallet']}\n")
            f.write(f"Receiver Wallet: {output_data['receiver_wallet']}\n")
            f.write(f"Receiver Address: {output_data['receiver_address']}\n")
            f.write(f"Amount Sent: {output_data['amount_sent']} BTC\n")
            f.write(f"Transaction Fee: {output_data['transaction_fee']} BTC\n")
            f.write(f"Confirmations: {output_data['confirmations']}\n")
            f.write(f"Transaction Size: {output_data['tx_size']} bytes\n")
            f.write(f"Transaction Virtual Size: {output_data['tx_vsize']} vbytes\n")
            f.write(f"Number of Inputs: {output_data['inputs']}\n")
            f.write(f"Number of Outputs: {output_data['outputs']}\n")
            f.write(f"Miner Balance Before: {output_data['miner_balance_before']} BTC\n")
            f.write(f"Miner Balance After: {output_data['miner_balance_after']} BTC\n")
            f.write(f"Trader Balance After: {output_data['trader_balance_after']} BTC\n")
        
        print(f"Transaction details written to: {output_file}")
        print("Script completed successfully!")

    except JSONRPCException as rpc_error:
        print(f"RPC Error occurred: {rpc_error}")
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    main()