import math

class FIRESimulator:
    def __init__(self):
        self.TAX_RATE = 0.20315  # 運用益にかかる税率
        self.NISA_LIFETIME_LIMIT = 1800  # NISA生涯投資枠（万円）

    def calculate(self, params):
        """
        シミュレーションを実行する
        """
        current_age = params.get('currentAge')
        current_assets = params.get('currentAssets')
        monthly_investment = params.get('monthlyInvestment')
        expected_return_pre = params.get('expectedReturnPre')
        fire_age = params.get('fireAge')
        living_expense = params.get('livingExpense')  # 月額
        expected_return_post = params.get('expectedReturnPost')
        inflation_rate = params.get('inflationRate')
        nisa_enabled = params.get('nisaEnabled', True)
        nisa_assets = params.get('nisaAssets', 0)
        nisa_limit_remaining = params.get('nisaLimitRemaining', 1800)
        pension_age = params.get('pensionAge', 65)
        pension_amount = params.get('pensionAmount', 15)  # 月額

        results = []
        age = current_age
        total_assets = current_assets
        regular_assets = current_assets - nisa_assets
        current_nisa_assets = nisa_assets
        remaining_nisa_limit = nisa_limit_remaining
        
        months_to_100 = (100 - current_age) * 12 # 100歳まで計算
        current_living_expense = living_expense
        exhaustion_age = None

        # 月次リターン（複利計算用）
        def get_monthly_rate(annual_rate):
            return math.pow(1 + annual_rate / 100, 1 / 12) - 1
            
        monthly_return_pre = get_monthly_rate(expected_return_pre)
        monthly_return_post = get_monthly_rate(expected_return_post)
        monthly_inflation_rate = get_monthly_rate(inflation_rate)

        for month in range(months_to_100 + 1):
            current_year = current_age + (month // 12)
            
            # 退職金の受取（リタイア開始月のみ）
            if month == (fire_age - current_age) * 12:
                regular_assets += params.get('retirementAllowance', 0)

            # 1年ごとのデータを記録
            if month % 12 == 0:
                results.append({
                    'age': current_year,
                    'totalAssets': max(0.0, total_assets),
                    'nisaAssets': max(0.0, current_nisa_assets),
                    'regularAssets': max(0.0, regular_assets)
                })

            if total_assets <= 0 and exhaustion_age is None:
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
                # 資産形成期：新規投資
                invest_amount = monthly_investment
                if nisa_enabled and remaining_nisa_limit > 0:
                    to_nisa = min(invest_amount, remaining_nisa_limit)
                    current_nisa_assets += to_nisa
                    remaining_nisa_limit -= to_nisa
                    invest_amount -= to_nisa
                regular_assets += invest_amount
            else:
                # FIRE後：取り崩し
                withdraw_amount = current_living_expense
                
                # 年金受給
                if current_year >= pension_age:
                    withdraw_amount -= pension_amount

                if withdraw_amount > 0:
                    # 特定口座から優先的に取り崩す
                    if regular_assets >= withdraw_amount:
                        regular_assets -= withdraw_amount
                    else:
                        remaining_to_withdraw = withdraw_amount - regular_assets
                        regular_assets = 0
                        current_nisa_assets -= remaining_to_withdraw
                else:
                    # 年金が生活費を上回る場合は余剰を特定口座へ
                    regular_assets += abs(withdraw_amount)

            # インフレによる生活費の増大
            current_living_expense *= (1 + monthly_inflation_rate)
            total_assets = current_nisa_assets + regular_assets

        return {
            'history': results,
            'exhaustionAge': exhaustion_age,
            'finalAssets': total_assets,
            'isSuccess': total_assets > 0 or exhaustion_age is None
        }

    def find_possible_fire_age(self, params):
        """
        FIRE可能年齢を逆算する
        """
        current_age = params.get('currentAge')
        
        # 1歳刻みで探索
        for test_age in range(current_age, 101):
            result = self.calculate({**params, 'fireAge': test_age})
            if result['isSuccess']:
                return test_age
        return None
