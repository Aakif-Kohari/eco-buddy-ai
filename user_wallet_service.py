class UserWalletService:
    """
    Manages the 'EcoCoins' digital currency. Users earn EcoCoins by taking
    sustainable actions and can spend them on premium features or community donations.
    """
    
    def __init__(self):
        # user_id -> balance
        self.balances = {}
        # Ledgers for audit
        self.transactions = []

    def get_balance(self, user_id: str) -> int:
        return self.balances.get(user_id, 0)

    def mint_coins(self, user_id: str, amount: int, reason: str):
        """Adds EcoCoins to a user's wallet (e.g. via recycling receipt upload)."""
        if amount <= 0:
            raise ValueError("Amount must be positive.")
            
        current = self.balances.get(user_id, 0)
        self.balances[user_id] = current + amount
        
        self.transactions.append({
            "user_id": user_id,
            "type": "MINT",
            "amount": amount,
            "reason": reason,
            "timestamp": "now"
        })
        return self.balances[user_id]

    def spend_coins(self, user_id: str, amount: int, reason: str) -> bool:
        """Deducts EcoCoins if the user has sufficient balance."""
        current = self.balances.get(user_id, 0)
        
        if current < amount:
            return False # Insufficient funds
            
        self.balances[user_id] = current - amount
        
        self.transactions.append({
            "user_id": user_id,
            "type": "SPEND",
            "amount": amount,
            "reason": reason,
            "timestamp": "now"
        })
        return True

    def transfer_to_charity(self, user_id: str, amount: int, charity_id: str) -> bool:
        """Allows users to donate EcoCoins to verified charities."""
        success = self.spend_coins(user_id, amount, f"Donation to {charity_id}")
        if success:
            # Here we would normally credit the charity account
            pass
        return success
