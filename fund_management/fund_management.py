from iconservice import *

TAG = 'FundManagement'


class FundPercentage(TypedDict):
    category: str
    percentage: int


class FundManagement(IconScoreBase):

    FUND_CATEGORIES = "fund_categories"
    FUND_CATEGORIES_ADDRESS = "fund_categories_address"
    FUND_CATEGORIES_PERCENTAGE = "fund_categories_percentage"

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._fund_categories = ArrayDB(self.FUND_CATEGORIES, db, value_type=str)
        self._fund_categories_address = DictDB(self.FUND_CATEGORIES_ADDRESS, db, value_type=Address)
        self._fund_categories_percentage = DictDB(self.FUND_CATEGORIES_PERCENTAGE, db, value_type=int)

    def on_install(self) -> None:
        super().on_install()

    def on_update(self) -> None:
        super().on_update()

    @eventlog(indexed=1)
    def FundTransferred(self, category: str, amount: str):
        pass
    
    @external(readonly=True)
    def name(self) -> str:
        return "ICONbet P-Rep fund management"

    @external(readonly=True)
    def get_fund_categories_address(self) -> dict:
        return {item: self._fund_categories_address[item] for item in self._fund_categories}

    @external(readonly=True)
    def get_fund_categories_percentage(self) -> dict:
        total_share = self.get_total_share()
        if total_share == 0:
            return {item: 0 for item in self._fund_categories}
        else:
            return {item: self._fund_categories_percentage[item] * 100/total_share for item in self._fund_categories}
    
    @external(readonly=True)
    def get_fund_categories_share(self) -> dict:
        return {item: str(self._fund_categories_percentage[item]) for item in self._fund_categories}

    @external(readonly=True)
    def get_total_share(self) -> int:
        total = 0
        for category in self._fund_categories:
            total += self._fund_categories_percentage[category]
        return total

    @external
    def add_fund_categories(self, _category: str, _address: Address, _share: int) -> None:

        if self.msg.sender != self.owner:
            revert(f"{TAG}: Only owner can add the fund category")

        if _category not in self._fund_categories:
            self._fund_categories.put(_category)
        self._fund_categories_address[_category] = _address
        self._fund_categories_percentage[_category] = _share

    @external
    def remove_fund_categories(self, _category: str) -> None:

        if self.msg.sender != self.owner:
            revert(f"{TAG}: Only owner can add the fund category")

        remove_array_item(self._fund_categories, _category)
        self._fund_categories_address.remove(_category)
        self._fund_categories_percentage.remove(_category)

    @payable
    @external
    def distribute(self) -> None:
        if len(self._fund_categories) == 0:
            revert(f"{TAG}: No fund categories has been set")

        total_amount = self.msg.value
        total_share = 0
        for each_category in self._fund_categories:
            total_share += self._fund_categories_percentage[each_category]

        if total_share == 0:
            revert(f"{TAG}: No percentage amount has been set for the available fund categories")

        for each_category in self._fund_categories:
            amount_share = (self._fund_categories_percentage[each_category] * total_amount) // total_share
            if amount_share > 0:
                self.icx.transfer(self._fund_categories_address[each_category], amount_share)
                self.FundTransferred(each_category, str(amount_share))
            total_amount -= amount_share
            total_share -= self._fund_categories_percentage[each_category]

            if total_amount == 0 or total_share == 0:
                return

    @payable
    def fallback(self) -> None:
        revert(f"{TAG}: This contract doesn't accept plain ICX")


def remove_array_item(array_db: ArrayDB, _target):
    if _target not in array_db:
        revert(f"FundManagement: {_target} not found in the array db. Can't be removed")
    out = array_db.pop()
    if out != _target:
        for index in range(0, len(array_db)):
            if array_db[index] == _target:
                array_db[index] = out
                return
