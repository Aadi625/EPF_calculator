from flask import Flask, render_template, request

app = Flask(__name__)


# =========================================================
# INDIAN NUMBER FORMAT
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

            pairs.insert(
                0,
                remaining[-2:]
            )

            remaining = remaining[:-2]

        if remaining:

            pairs.insert(
                0,
                remaining
            )

        formatted = (
            ",".join(pairs)
            + ","
            + last_three
        )

    return (
        "-" if negative else ""
    ) + formatted


app.jinja_env.filters["indian"] = indian_format


# =========================================================
# EPF PROJECTION ENGINE
# =========================================================

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

    # -----------------------------------------------------
    # IMPORTANT
    #
    # Inclusive calculation:
    #
    # Age 25 to Age 60
    # = 60 - 25 + 1
    # = 36 contribution years
    # -----------------------------------------------------

    years = (
        retirement_age
        - current_age
        + 1
    )


    balance = current_balance

    salary = monthly_salary


    total_employee = 0

    total_employer_epf = 0

    total_vpf = 0

    total_interest = 0


    yearly_data = []


    # =====================================================
    # PROJECTION WITH VPF
    # =====================================================

    for year in range(years):

        opening_balance = balance


        # -------------------------------------------------
        # ANNUAL EMPLOYEE EPF
        # -------------------------------------------------

        annual_employee = (
            salary
            * 12
            * employee_rate
        )


        # -------------------------------------------------
        # ANNUAL EMPLOYER EPF
        #
        # IMPORTANT:
        #
        # The employer_rate entered by the user is treated
        # as the amount ENTERING EPF directly.
        #
        # Example:
        # 3.67% means 3.67% goes into EPF.
        #
        # We DO NOT subtract EPS again.
        # -------------------------------------------------

        annual_employer_epf = (
            salary
            * 12
            * employer_rate
        )


        # -------------------------------------------------
        # ANNUAL VPF
        # -------------------------------------------------

        annual_vpf = (
            salary
            * 12
            * vpf_rate
        )


        # -------------------------------------------------
        # TOTAL CONTRIBUTION FOR THE YEAR
        # -------------------------------------------------

        annual_contribution = (
            annual_employee
            + annual_employer_epf
            + annual_vpf
        )


        # -------------------------------------------------
        # ADD CONTRIBUTION
        # -------------------------------------------------

        balance += annual_contribution


        # -------------------------------------------------
        # ANNUAL EPF INTEREST
        # -------------------------------------------------

        annual_interest = (
            balance
            * interest_rate
        )


        balance += annual_interest


        # -------------------------------------------------
        # ACCUMULATE TOTALS
        # -------------------------------------------------

        total_employee += (
            annual_employee
        )

        total_employer_epf += (
            annual_employer_epf
        )

        total_vpf += (
            annual_vpf
        )

        total_interest += (
            annual_interest
        )


        # -------------------------------------------------
        # SAVE YEARLY DATA FOR CHART
        # -------------------------------------------------

        yearly_data.append({

            "age":
                current_age + year,

            "salary":
                round(salary),

            "opening_balance":
                round(opening_balance),

            "employee":
                round(annual_employee),

            "employer":
                round(annual_employer_epf),

            "vpf":
                round(annual_vpf),

            "interest":
                round(annual_interest),

            "closing_balance":
                round(balance)

        })


        # -------------------------------------------------
        # SALARY INCREASE FOR NEXT YEAR
        # -------------------------------------------------

        salary *= (
            1 + salary_growth
        )


    # =====================================================
    # PROJECTION WITHOUT VPF
    # =====================================================

    no_vpf_balance = current_balance

    no_vpf_salary = monthly_salary


    for year in range(years):


        annual_employee = (
            no_vpf_salary
            * 12
            * employee_rate
        )


        annual_employer_epf = (
            no_vpf_salary
            * 12
            * employer_rate
        )


        annual_contribution = (
            annual_employee
            + annual_employer_epf
        )


        # Add annual contribution

        no_vpf_balance += (
            annual_contribution
        )


        # Apply annual interest

        no_vpf_interest = (
            no_vpf_balance
            * interest_rate
        )


        no_vpf_balance += (
            no_vpf_interest
        )


        # Salary increase

        no_vpf_salary *= (
            1 + salary_growth
        )


    # =====================================================
    # FINAL SALARY
    # =====================================================

    if years > 0:

        final_monthly_salary = (
            salary
            /
            (1 + salary_growth)
        )

    else:

        final_monthly_salary = (
            monthly_salary
        )


    # =====================================================
    # FINAL MONTHLY EMPLOYEE EPF
    # =====================================================

    final_employee_contribution = (
        final_monthly_salary
        * employee_rate
    )


    # =====================================================
    # VPF IMPACT
    # =====================================================

    additional_vpf_corpus = (
        balance
        - no_vpf_balance
    )


    # =====================================================
    # TOTAL CONTRIBUTIONS INTO EPF
    # =====================================================

    total_contributions_to_epf = (
        total_employee
        + total_employer_epf
        + total_vpf
    )


    # =====================================================
    # EPS
    #
    # Employer contribution input is already the EPF
    # component (for example 3.67%).
    #
    # Therefore EPS is NOT deducted from this amount.
    #
    # We return 0 because EPS is not part of the projected
    # EPF corpus under this calculation model.
    # =====================================================

    total_eps = 0


    # =====================================================
    # RETURN RESULTS
    # =====================================================

    return {

        "years":
            years,

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
            round(
                final_employee_contribution
            ),

        "without_vpf":
            round(no_vpf_balance),

        "with_vpf":
            round(balance),

        "additional_vpf_corpus":
            round(
                additional_vpf_corpus
            ),

        "total_contributions":
            round(
                total_contributions_to_epf
            ),

        "yearly_data":
            yearly_data

    }


# =========================================================
# MAIN ROUTE
# =========================================================

@app.route(
    "/",
    methods=[
        "GET",
        "POST"
    ]
)

def index():

    results = None

    error = None


    if request.method == "POST":

        try:

            # =================================================
            # REQUIRED INPUTS
            # =================================================

            current_age = int(
                request.form.get(
                    "current_age"
                )
            )


            retirement_age = int(
                request.form.get(
                    "retirement_age"
                )
            )


            monthly_salary = float(
                request.form.get(
                    "monthly_salary"
                )
            )


            employee_rate = (
                float(
                    request.form.get(
                        "employee_rate"
                    )
                )
                / 100
            )


            employer_rate = (
                float(
                    request.form.get(
                        "employer_rate"
                    )
                )
                / 100
            )


            vpf_rate = (
                float(
                    request.form.get(
                        "vpf_rate"
                    )
                )
                / 100
            )


            salary_growth = (
                float(
                    request.form.get(
                        "salary_growth"
                    )
                )
                / 100
            )


            interest_rate = (
                float(
                    request.form.get(
                        "interest_rate"
                    )
                )
                / 100
            )


            # =================================================
            # CURRENT EPF BALANCE
            # =================================================

            current_balance_raw = (
                request.form.get(
                    "current_balance"
                )
            )


            if (
                current_balance_raw is None
                or
                current_balance_raw.strip() == ""
            ):

                current_balance = 0

            else:

                current_balance = float(
                    current_balance_raw
                )


            # =================================================
            # VALIDATION
            # =================================================

            if current_age < 18:

                raise ValueError(
                    "Current age must be at least 18."
                )


            if retirement_age <= current_age:

                raise ValueError(
                    "Retirement age must be greater than current age."
                )


            if retirement_age > 100:

                raise ValueError(
                    "Please enter a valid retirement age."
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
                    "Employee EPF contribution cannot be negative."
                )


            if employer_rate < 0:

                raise ValueError(
                    "Employer EPF contribution cannot be negative."
                )


            if vpf_rate < 0:

                raise ValueError(
                    "VPF contribution cannot be negative."
                )


            if salary_growth < 0:

                raise ValueError(
                    "Salary growth cannot be negative."
                )


            if interest_rate < 0:

                raise ValueError(
                    "EPF interest rate cannot be negative."
                )


            # =================================================
            # RUN CALCULATION
            # =================================================

            projection = (
                calculate_epf_projection(

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
            )


            # =================================================
            # RESULT DATA
            # =================================================

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
                    round(
                        employee_rate * 100,
                        2
                    ),

                "employer_rate":
                    round(
                        employer_rate * 100,
                        2
                    ),

                "salary_growth":
                    round(
                        salary_growth * 100,
                        2
                    ),

                "vpf_rate":
                    round(
                        vpf_rate * 100,
                        2
                    ),

                "interest_rate":
                    round(
                        interest_rate * 100,
                        2
                    )

            }


        except (
            TypeError,
            ValueError
        ) as e:

            message = str(e)


            if (
                "invalid literal"
                in message
                or
                "float()"
                in message
                or
                "int()"
                in message
            ):

                error = (
                    "Please complete all required fields "
                    "before running the simulation."
                )

            else:

                error = message


        except Exception:

            error = (
                "Something went wrong while calculating "
                "your EPF projection. Please check your "
                "inputs and try again."
            )


    return render_template(

        "index.html",

        results=results,

        error=error

    )


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )
