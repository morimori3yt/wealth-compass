import math

class FIRESimulator:
    def __init__(self):
        self.DEFAULT_TAX_RATE = 0.20315  # デフォルト税率
        self.DEFAULT_NISA_LIMIT = 1800   # デフォルトNISA生涯枠

    def calculate(self, params):
        """
        FIREシミュレーションを実行する (3シナリオ対応)
        """
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
        """
        単一のシナリオでシミュレーションを実行
        """
        current_age = params.get('currentAge', 30)
        current_assets = params.get('currentAssets', 500)
        monthly_investment = params.get('monthlyInvestment', 10)
        fire_age = params.get('fireAge', 50)
        living_expense = params.get('livingExpense', 25)
        inflation_rate = params.get('inflationRate', 1.0)
        nisa_assets = params.get('nisaAssets', 100)
        
        # 新規追加項目
        nisa_limit_remaining = params.get('nisaLimitRemaining', 1700)
        tax_rate = params.get('taxRate', 20.315) / 100.0
        
        pension_age = params.get('pensionAge', 65)
        pension_amount = params.get('pensionAmount', 15)
        retirement_allowance = params.get('retirementAllowance', 0)

        history = []
        regular_assets = current_assets - nisa_assets
        current_nisa_assets = nisa_assets
        total_assets = current_assets
        remaining_nisa_limit = nisa_limit_remaining
        
        current_living_expense = living_expense
        exhaustion_age = None

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
                history.append({
                    'age': current_year,
                    'totalAssets': round(max(0.0, total_assets), 2),
                    'nisaAssets': round(max(0.0, current_nisa_assets), 2),
                    'regularAssets': round(max(0.0, regular_assets), 2)
                })

            if total_assets <= 0 and exhaustion_age is None and current_year >= fire_age:
                exhaustion_age = current_year

            is_pre_fire = current_year < fire_age
            current_rate = monthly_return_pre if is_pre_fire else monthly_return_post

            nisa_gains = current_nisa_assets * current_rate
            current_nisa_assets += nisa_gains

            # 指定された税率を使用
            regular_gains = regular_assets * current_rate * (1 - tax_rate)
            regular_assets += regular_gains

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
                if current_year >= pension_age:
                    withdraw_amount -= pension_amount

                if withdraw_amount > 0:
                    if regular_assets >= withdraw_amount:
                        regular_assets -= withdraw_amount
                    else:
                        remaining_to_withdraw = withdraw_amount - regular_assets
                        regular_assets = 0
                        current_nisa_assets = max(0, current_nisa_assets - remaining_to_withdraw)
                else:
                    regular_assets += abs(withdraw_amount)

            current_living_expense *= (1 + monthly_inflation_rate)
            total_assets = current_nisa_assets + regular_assets

        return {
            'history': history,
            'exhaustionAge': exhaustion_age,
            'finalAssets': round(max(0.0, total_assets), 2)
        }

    def find_possible_fire_age(self, params):
        current_age = params.get('currentAge', 30)
        for test_age in range(current_age, 101):
            if self._is_fire_possible(params, test_age):
                return test_age
        return None

    def _is_fire_possible(self, params, test_age):
        p = {**params, 'fireAge': test_age}
        res = self._calculate_single_scenario(p, p['expectedReturnPre'], p['expectedReturnPost'])
        return res['finalAssets'] > 0 and res['exhaustionAge'] is None
