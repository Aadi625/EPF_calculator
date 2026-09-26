from flask import Flask, render_template, request

app = Flask(__name__)


# =========================================================
# CONFIGURATION
# =========================================================

EPS_RATE = 8.33 / 100
EPS_WAGE_CEILING = 15000


# =========================================================
# HELPERS
# =========================================================

def indian_format(value):
    try:
        value = round(float(value))
    except (ValueError, TypeError):
        return "0"

    negative = value < 0
    value = abs(value)

    number = str(value)

    if len(number) <= 3:
        formatted = number

    else:
        last_three = number[-3:]
        remaining = number[:-3]

        pairs = []

        while len(remaining) > 2:
            pairs.insert(0, remaining[-2:])
            remaining = remaining[:-2]

        if remaining:
            pairs.insert(0, remaining)

        formatted = ",".join(pairs) + "," + last_three

    return ("-" if negative else "") + formatted


app.jinja_env.filters["indian"] = indian_format


def calculate_epf_projection(
    current_age,
    retirement_age,
    monthly_salary,
    current_balance,
    employee_rate,
    employer_rate,
    salary_growth,
    vpf_rate,
    interest_rate
):

    years = retirement_age - current_age + 1

    balance = current_balance
    salary = monthly_salary

    total_employee = 0
    total_employer_epf = 0
    total_eps = 0
    total_vpf = 0
    total_interest = 0

    yearly_data = []

    # -----------------------------------------
    # Projection WITH VPF
    # -----------------------------------------

    for year in range(years):

        opening_balance = balance

        yearly_employee = 0
        yearly_employer = 0
        yearly_eps = 0
        yearly_vpf = 0
        yearly_interest = 0

        for month in range(12):

            employee_contribution = (
                salary * employee_rate
            )

            employer_total = (
                salary * employer_rate
            )

            # EPS is modeled at 8.33%
            # subject to pension wage ceiling.

            pensionable_salary = min(
                salary,
                EPS_WAGE_CEILING
            )

            eps_contribution = (
                pensionable_salary
                * EPS_RATE
            )

            # EPS cannot exceed modeled
            # employer contribution.

            eps_contribution = min(
                eps_contribution,
                employer_total
            )

            employer_epf = (
                employer_total
                - eps_contribution
            )

            vpf_contribution = (
                salary * vpf_rate
            )

            monthly_contribution = (
                employee_contribution
                + employer_epf
                + vpf_contribution
            )

            # Monthly approximation of
            # annual EPF interest rate.

            monthly_interest = (
                balance
                * (interest_rate / 12)
            )

            balance += (
                monthly_interest
                + monthly_contribution
            )

            yearly_employee += (
                employee_contribution
            )

            yearly_employer += (
                employer_epf
            )

            yearly_eps += (
                eps_contribution
            )

            yearly_vpf += (
                vpf_contribution
            )

            yearly_interest += (
                monthly_interest
            )

        total_employee += yearly_employee
        total_employer_epf += yearly_employer
        total_eps += yearly_eps
        total_vpf += yearly_vpf
        total_interest += yearly_interest

        yearly_data.append({
            "age": current_age + year + 1,
            "salary": round(salary),
            "opening_balance": round(opening_balance),
            "employee": round(yearly_employee),
            "employer": round(yearly_employer),
            "vpf": round(yearly_vpf),
            "interest": round(yearly_interest),
            "closing_balance": round(balance)
        })

        salary *= (1 + salary_growth)


    # =====================================================
    # SECOND PROJECTION — WITHOUT VPF
    # =====================================================

    no_vpf_balance = current_balance
    no_vpf_salary = monthly_salary

    for year in range(years):

        for month in range(12):

            employee_contribution = (
                no_vpf_salary
                * employee_rate
            )

            employer_total = (
                no_vpf_salary
                * employer_rate
            )

            pensionable_salary = min(
                no_vpf_salary,
                EPS_WAGE_CEILING
            )

            eps_contribution = (
                pensionable_salary
                * EPS_RATE
            )

            eps_contribution = min(
                eps_contribution,
                employer_total
            )

            employer_epf = (
                employer_total
                - eps_contribution
            )

            monthly_interest = (
                no_vpf_balance
                * (interest_rate / 12)
            )

            no_vpf_balance += (
                monthly_interest
                + employee_contribution
                + employer_epf
            )

        no_vpf_salary *= (
            1 + salary_growth
        )


    # =====================================================
    # FINAL VALUES
    # =====================================================

    final_monthly_salary = salary / (
        1 + salary_growth
    )

    final_employee_contribution = (
        final_monthly_salary
        * employee_rate
    )

    additional_vpf_corpus = (
        balance - no_vpf_balance
    )

    total_contributions_to_epf = (
        total_employee
        + total_employer_epf
        + total_vpf
    )

    return {

        "years": years,

        "projected_corpus":
            round(balance),

        "employee_contribution":
            round(total_employee),

        "employer_epf_contribution":
            round(total_employer_epf),

        "vpf_contribution":
            round(total_vpf),

        "eps_contribution":
            round(total_eps),

        "interest_earned":
            round(total_interest),

        "final_salary":
            round(final_monthly_salary),

        "final_employee_monthly":
            round(final_employee_contribution),

        "without_vpf":
            round(no_vpf_balance),

        "with_vpf":
            round(balance),

        "additional_vpf_corpus":
            round(additional_vpf_corpus),

        "total_contributions":
            round(total_contributions_to_epf),

        "yearly_data":
            yearly_data
    }


# =========================================================
# ROUTE
# =========================================================

@app.route("/", methods=["GET", "POST"])
def index():

    results = None
    error = None

    if request.method == "POST":

        try:

            current_age = int(
                request.form.get(
                    "current_age",
                    0
                )
            )

            retirement_age = int(
                request.form.get(
                    "retirement_age",
                    0
                )
            )

            monthly_salary = float(
                request.form.get(
                    "monthly_salary",
                    0
                ) or 0
            )

            current_balance = float(
                request.form.get(
                    "current_balance",
                    0
                ) or 0
            )

            employee_rate = float(
                request.form.get(
                    "employee_rate",
                    12
                ) or 12
            ) / 100

            employer_rate = float(
                request.form.get(
                    "employer_rate",
                    12
                ) or 12
            ) / 100

            salary_growth = float(
                request.form.get(
                    "salary_growth",
                    8
                ) or 0
            ) / 100

            vpf_rate = float(
                request.form.get(
                    "vpf_rate",
                    0
                ) or 0
            ) / 100

            interest_rate = float(
                request.form.get(
                    "interest_rate",
                    8.25
                ) or 0
            ) / 100


            # -----------------------------------------
            # VALIDATION
            # -----------------------------------------

            if current_age < 18:
                raise ValueError(
                    "Current age must be at least 18."
                )

            if retirement_age <= current_age:
                raise ValueError(
                    "Retirement age must be greater than current age."
                )

            if monthly_salary <= 0:
                raise ValueError(
                    "Monthly Basic Salary + DA must be greater than zero."
                )

            if current_balance < 0:
                raise ValueError(
                    "Current EPF balance cannot be negative."
                )

            if employee_rate < 0:
                raise ValueError(
                    "Employee contribution cannot be negative."
                )

            if employer_rate < 0:
                raise ValueError(
                    "Employer contribution cannot be negative."
                )

            if salary_growth < 0:
                raise ValueError(
                    "Salary growth cannot be negative."
                )

            if vpf_rate < 0:
                raise ValueError(
                    "VPF contribution cannot be negative."
                )

            if interest_rate < 0:
                raise ValueError(
                    "Interest rate cannot be negative."
                )


            # -----------------------------------------
            # CALCULATE
            # -----------------------------------------

            projection = calculate_epf_projection(

                current_age,
                retirement_age,
                monthly_salary,
                current_balance,
                employee_rate,
                employer_rate,
                salary_growth,
                vpf_rate,
                interest_rate

            )


            results = {

                **projection,

                "current_age":
                    current_age,

                "retirement_age":
                    retirement_age,

                "monthly_salary":
                    monthly_salary,

                "current_balance":
                    current_balance,

                "employee_rate":
                    employee_rate * 100,

                "employer_rate":
                    employer_rate * 100,

                "salary_growth":
                    salary_growth * 100,

                "vpf_rate":
                    vpf_rate * 100,

                "interest_rate":
                    interest_rate * 100
            }


        except ValueError as e:
            error = str(e)

        except Exception:
            error = (
                "Something went wrong while calculating "
                "your EPF projection."
            )


    return render_template(
        "index.html",
        results=results,
        error=error
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    app.run(debug=True)
