import math

class FIRESimulator:
    def __init__(self):
        self.TAX_RATE = 0.20315  # 運用益にかかる税率（簡易計算用）
        self.NISA_LIFETIME_LIMIT = 1800  # NISA生涯投資枠（万円）

    def calculate(self, params):
        """
        FIREシミュレーションを実行する (3シナリオ対応)
        """
        # 通常(Base)の利回り
        base_pre = params.get('expectedReturnPre', 5.0)
        base_post = params.get('expectedReturnPost', 3.0)
        
        # 強気(Bull)と弱気(Bear)の利回り設定
        # デフォルトで±2%とするが、入力があればそれを使う
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
        living_expense = params.get('livingExpense', 25)  # 月額
        inflation_rate = params.get('inflationRate', 1.0)
        nisa_assets = params.get('nisaAssets', 100)
        pension_age = params.get('pensionAge', 65)
        pension_amount = params.get('pensionAmount', 15)  # 月額
        retirement_allowance = params.get('retirementAllowance', 0)

        history = []
        regular_assets = current_assets - nisa_assets
        current_nisa_assets = nisa_assets
        total_assets = current_assets
        remaining_nisa_limit = max(0, self.NISA_LIFETIME_LIMIT - nisa_assets)
        
        current_living_expense = living_expense
        exhaustion_age = None

        # 月次リターン
        def get_monthly_rate(annual_rate):
            if annual_rate <= 0: return 0.0
            return math.pow(1 + annual_rate / 100, 1 / 12) - 1
            
        monthly_return_pre = get_monthly_rate(ret_pre)
        monthly_return_post = get_monthly_rate(ret_post)
        monthly_inflation_rate = get_monthly_rate(inflation_rate)

        months_to_100 = (100 - current_age) * 12

        for month in range(months_to_100 + 1):
            current_year = current_age + (month // 12)
            
            # 退職金の受取（リタイア開始月のみ）
            if month == int((fire_age - current_age) * 12):
                regular_assets += retirement_allowance

            # 1年ごとのデータを記録
            if month % 12 == 0:
                history.append({
                    'age': current_year,
                    'totalAssets': round(max(0.0, total_assets), 2),
                    'nisaAssets': round(max(0.0, current_nisa_assets), 2),
                    'regularAssets': round(max(0.0, regular_assets), 2)
                })

            if total_assets <= 0 and exhaustion_age is None and current_year >= fire_age:
                exhaustion_age = current_year

            # 運用益の計算
            is_pre_fire = current_year < fire_age
            current_rate = monthly_return_pre if is_pre_fire else monthly_return_post

            # NISA枠の運用（非課税）
            nisa_gains = current_nisa_assets * current_rate
            current_nisa_assets += nisa_gains

            # 特定口座の運用（課税考慮）
            regular_gains = regular_assets * current_rate * (1 - self.TAX_RATE)
            regular_assets += regular_gains

            # 収入と支出
            if is_pre_fire:
                # 資産形成期
                invest_amount = monthly_investment
                # NISA枠を優先消費（月30万までなどの細かい制限は今回省略し、生涯枠のみ考慮）
                if remaining_nisa_limit > 0:
                    to_nisa = min(invest_amount, remaining_nisa_limit)
                    current_nisa_assets += to_nisa
                    remaining_nisa_limit -= to_nisa
                    invest_amount -= to_nisa
                regular_assets += invest_amount
            else:
                # FIRE後
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

            # インフレと合計算出
            current_living_expense *= (1 + monthly_inflation_rate)
            total_assets = current_nisa_assets + regular_assets

        return {
            'history': history,
            'exhaustionAge': exhaustion_age,
            'finalAssets': round(max(0.0, total_assets), 2)
        }

    def find_possible_fire_age(self, params):
        """
        FIRE可能年齢を逆算する (通常シナリオ基準)
        """
        current_age = params.get('currentAge', 30)
        for test_age in range(current_age, 101):
            # 通常シナリオのみで判定
            res = self._calculate_single_scenario(params, params['expectedReturnPre'], params['expectedReturnPost'])
            if res['finalAssets'] > 0 and res['exhaustionAge'] is None:
                return test_age
            # 再計算を避けるため、内部で一度回す必要があるが、ここでは簡略化
            # 本来は _calculate_single_scenario の結果を見て test_age を返す
            if self._is_fire_possible(params, test_age):
                return test_age
        return None

    def _is_fire_possible(self, params, test_age):
        p = {**params, 'fireAge': test_age}
        res = self._calculate_single_scenario(p, p['expectedReturnPre'], p['expectedReturnPost'])
        return res['finalAssets'] > 0 and res['exhaustionAge'] is None
