import math

class FIRESimulator:
    def __init__(self):
        self.DEFAULT_TAX_RATE = 0.20315
        self.DEFAULT_NISA_LIMIT = 1800

    def calculate(self, params):
        base_pre = params.get('expectedReturnPre', 5.0)
        base_post = params.get('expectedReturnPost', 3.0)
        bull_pre = params.get('expectedReturnPreBull', base_pre + 2.0)
        bull_post = params.get('expectedReturnPostBull', base_post + 2.0)
        bear_pre = params.get('expectedReturnPreBear', max(0.0, base_pre - 2.0))
        bear_post = params.get('expectedReturnPostBear', max(0.0, base_post - 2.0))

        scenarios = {
            '通常': {'pre': base_pre, 'post': base_post},
            '強気': {'pre': bull_pre, 'post': bull_post},
            '弱気': {'pre': bear_pre, 'post': bear_post}
        }
        
        results = {}
        for name, ret in scenarios.items():
            results[name] = self._calculate_single_scenario(params, ret['pre'], ret['post'])
        return results

    def _calculate_single_scenario(self, params, ret_pre, ret_post):
        current_age = params.get('currentAge', 30)
        current_assets = params.get('currentAssets', 500)
        monthly_investment = params.get('monthlyInvestment', 10)
        fire_age = params.get('fireAge', 50)
        living_expense = params.get('livingExpense', 25)
        inflation_rate = params.get('inflationRate', 1.0)
        nisa_assets = params.get('nisaAssets', 100)
        nisa_limit_remaining = params.get('nisaLimitRemaining', 1700)
        tax_rate = params.get('taxRate', 20.315) / 100.0
        pension_age = params.get('pensionAge', 65)
        pension_amount = params.get('pensionAmount', 15)
        retirement_allowance = params.get('retirementAllowance', 0)
        
        # サイドFIRE用パラメータ
        use_side_fire = params.get('useSideFire', False)
        side_income = params.get('sideIncome', 0.0)
        side_income_age = params.get('sideIncomeAge', 65)

        history = []
        regular_assets = current_assets - nisa_assets
        current_nisa_assets = nisa_assets
        total_assets = current_assets
        remaining_nisa_limit = nisa_limit_remaining
        current_living_expense = living_expense
        exhaustion_age = None
        total_withdrawal = 0.0

        def get_monthly_rate(annual_rate):
            if annual_rate <= 0: return 0.0
            return math.pow(1 + annual_rate / 100, 1 / 12) - 1
            
        monthly_return_pre = get_monthly_rate(ret_pre)
        monthly_return_post = get_monthly_rate(ret_post)
        monthly_inflation_rate = get_monthly_rate(inflation_rate)

        months_to_100 = (100 - current_age) * 12

        for month in range(months_to_100 + 1):
            current_year = current_age + (month // 12)
            if month == int((fire_age - current_age) * 12):
                regular_assets += retirement_allowance
            if month % 12 == 0:
                history.append({'age': current_year, 'totalAssets': round(max(0.0, total_assets), 2)})
            if total_assets <= 0 and exhaustion_age is None and current_year >= fire_age:
                exhaustion_age = current_year
            is_pre_fire = current_year < fire_age
            current_rate = monthly_return_pre if is_pre_fire else monthly_return_post
            current_nisa_assets += current_nisa_assets * current_rate
            regular_assets += regular_assets * current_rate * (1 - tax_rate)
            if is_pre_fire:
                invest_amount = monthly_investment
                if remaining_nisa_limit > 0:
                    to_nisa = min(invest_amount, remaining_nisa_limit)
                    current_nisa_assets += to_nisa
                    remaining_nisa_limit -= to_nisa
                    invest_amount -= to_nisa
                regular_assets += invest_amount
            else:
                withdraw_amount = current_living_expense
                if use_side_fire and current_year < side_income_age:
                    withdraw_amount -= (side_income / 12)
                if current_year >= pension_age: withdraw_amount -= pension_amount
                if withdraw_amount > 0:
                    actual_withdrawal = min(withdraw_amount, regular_assets + current_nisa_assets)
                    total_withdrawal += actual_withdrawal
                    if regular_assets >= withdraw_amount: regular_assets -= withdraw_amount
                    else:
                        remaining = withdraw_amount - regular_assets
                        regular_assets = 0
                        current_nisa_assets = max(0, current_nisa_assets - remaining)
                else: regular_assets += abs(withdraw_amount)
            current_living_expense *= (1 + monthly_inflation_rate)
            total_assets = current_nisa_assets + regular_assets

        return {'history': history, 'exhaustionAge': exhaustion_age, 'finalAssets': round(max(0.0, total_assets), 2), 'totalWithdrawal': round(total_withdrawal, 2)}

    def find_all_fire_ages(self, params):
        """
        全シナリオの最短FIRE年齢を算出
        """
        results = {}
        base_pre = params.get('expectedReturnPre', 5.0)
        base_post = params.get('expectedReturnPost', 3.0)
        
        scenarios = {
            '通常': {'pre': base_pre, 'post': base_post},
            '強気': {'pre': params.get('expectedReturnPreBull', base_pre + 2.0), 'post': params.get('expectedReturnPostBull', base_post + 2.0)},
            '弱気': {'pre': params.get('expectedReturnPreBear', max(0.0, base_pre - 2.0)), 'post': params.get('expectedReturnPostBear', max(0.0, base_post - 2.0))}
        }

        for name, ret in scenarios.items():
            results[name] = self.find_possible_fire_age_for_rates(params, ret['pre'], ret['post'])
        return results

    def find_possible_fire_age_for_rates(self, params, ret_pre, ret_post):
        current_age = params.get('currentAge', 30)
        for test_age in range(current_age, 101):
            p = {**params, 'fireAge': test_age}
            res = self._calculate_single_scenario(p, ret_pre, ret_post)
            if res['finalAssets'] > 0 and res['exhaustionAge'] is None:
                return test_age
        return None
