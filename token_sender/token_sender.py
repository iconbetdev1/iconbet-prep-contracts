from iconservice import *

TAG = 'TokenSender'
ICX_TO_COMP_TOKEN = 20


class Distribution(TypedDict):
    address: Address
    value: int


class TokenInterface(InterfaceScore):

    @interface
    def transfer(self, _to: Address, _value: int, _data: bytes = None):
        pass

    @interface
    def mint(self, _value: int, _to: Address = None) -> None:
        pass

    @interface
    def balanceOf(self, _owner: Address) -> int:
        pass

    @interface
    def name(self) -> str:
        pass


class TokenSender(IconScoreBase):
    ACCEPTED_TOKENS = "accepted_tokens"

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._accepted_tokens = ArrayDB(self.ACCEPTED_TOKENS, db, value_type=Address)

    def on_install(self) -> None:
        super().on_install()

    def on_update(self) -> None:
        super().on_update()

    @eventlog(indexed=1)
    def FundReceived(self, value: int):
        pass

    @external(readonly=True)
    def name(self) -> str:
        return TAG

    @external
    def add_accepted_tokens(self, _token: Address) -> None:
        """
        Add the token address which can be distributed through this contract
        :param _token: Address of the token which is to be distributed
        :return:
        """
        self._validate_owner()
        if not _token.is_contract:
            revert(f"{TAG}: {_token} is not a valid contract address")

        if _token not in self._accepted_tokens:
            self._accepted_tokens.put(_token)

    @external
    def remove_accepted_tokens(self, _token: Address) -> None:
        self._validate_owner()
        remove_array_item(self._accepted_tokens, _token)

    @external(readonly=True)
    def get_accepted_tokens(self) -> list:
        return [item for item in self._accepted_tokens]

    @external
    def mint_and_distribute_comp(self, _token: Address, _distributions: List[Distribution]) -> None:
        self._validate_owner()
        if _token not in self._accepted_tokens:
            revert(f"{TAG}: {_token} is not an accepted tokens for distribution")

        for receiver in _distributions:
            token_amount = receiver["value"]
            token_address = receiver["address"]
            icx_amount = token_amount // ICX_TO_COMP_TOKEN
            try:
                if token_amount > ICX_TO_COMP_TOKEN * 100:
                    token_contract = self.create_interface_score(_token, TokenInterface)
                    token_contract.icx(icx_amount).mint(token_amount, token_address)
            except BaseException as e:
                if not token_address.is_contract:
                    revert(f"{TAG}: Error in minting {token_amount} COMP token to {token_address}"
                           f"Error: {e}")

    @external
    def distribute_token(self, _token: Address, _distributions: List[Distribution]) -> None:
        self._validate_owner()
        if _token not in self._accepted_tokens:
            revert(f"{TAG}: {_token} is not an accepted tokens for distribution")

        for receiver in _distributions:
            try:
                token_contract = self.create_interface_score(_token, TokenInterface)
                token_contract.transfer(receiver["address"], receiver["value"], b'Token distribution from TokenSender')
            except BaseException as e:
                if not receiver["address"].is_contract:
                    revert(f"{TAG}: Error in sending distributing {receiver['value']} tokens to {receiver['address']}"
                           f"Error: {e}")

    @external
    def tokenFallback(self, _from: Address, _value: int, _data: bytes):
        self._validate_owner()
        if self.msg.sender not in self._accepted_tokens:
            revert(f"{TAG}: {self.msg.sender} is not a valid token to be distributed")

    @payable
    def fallback(self) -> None:
        if self.msg.sender != self.owner:
            revert(f"{TAG}: Only owner can add ICX to this contract")
        self.FundReceived(self.msg.value)

    @external
    def claim_ICX(self, _amount: int = 0) -> None:
        self._validate_owner()

        if _amount < 0:
            revert(f"{TAG}: Invalid amount of tokens provided")
        claim_amount = self.icx.get_balance(self.address) if _amount == 0 else _amount
        try:
            self.icx.transfer(self.msg.sender, claim_amount)
        except BaseException as e:
            revert(f"{TAG}: Error in claiming ICX from token sender contract /"
                   f"Reason: {e}")

    @external(readonly=True)
    def get_token_balance_in_contract(self) -> list:
        response = []
        for token in self._accepted_tokens:
            item = {}
            token_score = self.create_interface_score(token, TokenInterface)
            item["address"] = token
            item["name"] = token_score.name()
            item["balance"] = token_score.balanceOf(self.address)
            response.append(item)
        return response

    @external
    def claim_token(self, _token: Address, _amount: int = 0) -> None:
        self._validate_owner()

        if _amount < 0:
            revert(f"{TAG}: Invalid amount of tokens provided")

        if _token not in self._accepted_tokens:
            revert(f"{TAG}: {_token} is not an accepted tokens for claim")

        token_score = self.create_interface_score(_token, TokenInterface)
        claim_amount = token_score.balanceOf(self.address) if _amount == 0 else _amount
        try:
            token_score.transfer(self.msg.sender, claim_amount, b'Token claimed back from token sender contract')
        except BaseException as e:
            revert(f"{TAG}: Error in claiming tokens from token sender contract /"
                   f"Reason: {e}")

    def _validate_owner(self):
        if self.msg.sender != self.owner:
            revert(f"{TAG}: Only owner can call this method")


def remove_array_item(array_db: ArrayDB, _target):
    if _target not in array_db:
        revert(f"TokenSender: {_target} not found in the array db. Can't be removed")
    out = array_db.pop()
    if out != _target:
        for index in range(0, len(array_db)):
            if array_db[index] == _target:
                array_db[index] = out
                return
