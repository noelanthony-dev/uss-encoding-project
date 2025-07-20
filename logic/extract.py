import pandas as pd

def extract_data(modifier_file, item_file, discount_file, payment_file, branch):
    result = {}

    # --- PAYMENT FILE: Extract negative GCash amount ---
    if payment_file:
        if payment_file.name.endswith(".csv"):
            df_payment = pd.read_csv(payment_file)
        else:
            df_payment = pd.read_excel(payment_file)

        # Normalize columns
        df_payment.columns = [col.strip().lower().replace(" ", "_") for col in df_payment.columns]
        payment_type_col = None
        for col in df_payment.columns:
            if "payment" in col and "type" in col:
                payment_type_col = col
                break
        if not payment_type_col:
            payment_type_col = df_payment.columns[0]  # fallback

        df_payment[payment_type_col] = df_payment[payment_type_col].astype(str).str.strip().str.lower()

        # Try matching 'gcash' case-insensitively
        gcash_row = df_payment[df_payment[payment_type_col].str.lower() == "gcash"]

        if not gcash_row.empty:
            amount_column = df_payment.columns[-1]  # Use last column
            amount = gcash_row[amount_column].values[0]
            try:
                amount = float(str(amount).replace(",", ""))
                result["gcash"] = -amount
            except:
                result["gcash"] = ""

    # --- DISCOUNT FILE: Add Senior Citizen + PWD ---
    if discount_file:
        if discount_file.name.endswith(".csv"):
            discount_file.seek(0)
            df_discount = pd.read_csv(discount_file)
        else:
            df_discount = pd.read_excel(discount_file)

        df_discount.columns = [col.strip().lower() for col in df_discount.columns]
        row_names = df_discount.iloc[:, 0].astype(str).str.strip().str.lower()
        amount_col = df_discount.columns[-1]

        total_discount = 0
        for keyword in ["senior citizen", "pwd"]:
            match = df_discount[row_names == keyword]
            if not match.empty:
                val = match[amount_col].values[0]
                try:
                    total_discount += float(str(val).replace(",", ""))
                except:
                    continue

        if total_discount != 0:
            result["sc/pwd discounts"] = -total_discount

        # Handle Gift Certificate row and map to "Special Discounts"
        gc_match = df_discount[row_names == "gift certificate"]
        if not gc_match.empty:
            gc_val = gc_match[amount_col].values[0]
            try:
                gc_amount = float(str(gc_val).replace(",", ""))
                result["special discounts"] = -gc_amount
            except:
                pass

        # Handle Special Discount row and map to "special discount"
        special_match = df_discount[row_names == "special discount"]
        if not special_match.empty:
            special_val = special_match[amount_col].values[0]
            try:
                special_amount = float(str(special_val).replace(",", ""))
                result["special discount"] = -special_amount
            except:
                pass

    # --- ITEM FILE: Extract sold counts from specific items ---
    if item_file:
        if item_file.name.endswith(".csv"):
            item_file.seek(0)
            df_item = pd.read_csv(item_file)
        else:
            df_item = pd.read_excel(item_file)

        df_item.columns = [col.strip().lower() for col in df_item.columns]
        item_col = df_item.columns[0]
        sold_col = None
        for col in df_item.columns:
            if "item" in col and "sold" in col:
                sold_col = col
                break
        if not sold_col:
            sold_col = df_item.columns[-1]  # fallback

        df_item[item_col] = df_item[item_col].astype(str).str.strip()
        wanted_items = [
            "Combo S1",
            "Combo S2",
            "Combo S3",
            "Sandwich Sampler",
            "Regular - Aloha",
            "Regular - Breakfast",
            "Regular - Chicken Pesto",
            "Regular - Pizza Panino",
            "Regular - Tuna Melt Chive",
            "Regular - Vegan",
            "Salad - Chicken Salad",
            "Salad - Chickpeas Salad",
            "Salad - Green Salad",
            "Salad - Tuna Salad",
            "Snack - Aloha",
            "Snack - Breakfast",
            "Snack - Chicken Pesto",
            "Snack - Pizza Panino",
            "Snack - Tuna Melt Chive",
            "Snack - Vegan"
        ]
        for item in wanted_items:
            match = df_item[df_item[item_col].str.lower() == item.lower()]
            if not match.empty:
                val = match[sold_col].values[0]
                try:
                    qty = float(str(val).replace(",", ""))
                    if qty != 0:
                        result[item.lower()] = qty
                except:
                    continue

    # --- MODIFIER FILE: Process ingredients and modifiers ---
    if modifier_file:
        if modifier_file.name.endswith(".csv"):
            modifier_file.seek(0)
            df_mod = pd.read_csv(modifier_file)
        else:
            df_mod = pd.read_excel(modifier_file)

        df_mod.columns = [col.strip().lower() for col in df_mod.columns]
        mod_option_col = next((col for col in df_mod.columns if "option" in col), df_mod.columns[0])
        mod_name_col = next((col for col in df_mod.columns if "modifier" in col), df_mod.columns[1])
        qty_col = next((col for col in df_mod.columns if "quantity" in col or "sold" in col), df_mod.columns[-1])

        df_mod[mod_option_col] = df_mod[mod_option_col].astype(str).str.strip().str.lower()
        df_mod[mod_name_col] = df_mod[mod_name_col].astype(str).str.strip().str.lower()

        def get_qty(option):
            print(f"Fetching qty for option: {option}")
            match = df_mod[df_mod[mod_option_col] == option.lower()]
            return float(match[qty_col].values[0]) if not match.empty else 0

        def get_qty_if_contains(option, keyword):
            match = df_mod[(df_mod[mod_option_col] == option.lower()) & (df_mod[mod_name_col].str.contains(keyword.lower()))]
            return float(match[qty_col].values[0]) if not match.empty else 0

        # Bread: Only include quantity sold where modifier name contains "Choose your Grain"
        for bread in ["Ciabatta", "Brioche", "Multigrain"]:
            match = df_mod[
                (df_mod[mod_option_col] == bread.lower()) &
                (df_mod[mod_name_col].str.contains("choose your grain"))
            ]
            qty = float(match[qty_col].values[0]) if not match.empty else 0
            if qty != 0:
                result[bread.lower()] = qty

        # Free veggies - only include where modifier name contains "Choose your Veggies"
        for veg in ["Cucumber", "Lettuce", "Tomato", "White Onion"]:
            match = df_mod[
                (df_mod[mod_option_col] == veg.lower()) &
                (df_mod[mod_name_col].str.contains("choose your veggies"))
            ]
            qty = float(match[qty_col].values[0]) if not match.empty else 0
            if qty != 0:
                result[veg.lower()] = qty

        # Proteins (only if modifier name contains "Choose your Meat")
        for meat in ["Bacon", "Beef Salami", "Ham", "Honey Ham", "Italian Chicken", "Tuna Flakes", "Chickpeas"]:
            match = df_mod[
                (df_mod[mod_option_col] == meat.lower()) &
                (df_mod[mod_name_col].str.contains("choose your meat"))
            ]
            qty = float(match[qty_col].values[0]) if not match.empty else 0
            if qty != 0:
                result[meat.lower()] = qty

        # Cheese - only include where modifier name contains "Choose your Cheese"
        for cheese in ["Cheddar", "Mozzarella", "Two Cheese"]:
            match = df_mod[
                (df_mod[mod_option_col] == cheese.lower()) &
                (df_mod[mod_name_col].str.contains("choose your cheese"))
            ]
            qty = float(match[qty_col].values[0]) if not match.empty else 0
            if qty != 0:
                result[cheese.lower()] = qty

        # Sauces (only if modifier name contains "Choose your Spread")
        for sauce in ["Balsamic Vinaigrette", "Cream Cheese & Chive", "Garlic Ranch", "Honey Mustard", "Pesto Cream", "Ultimate Aioli"]:
            match = df_mod[
                (df_mod[mod_option_col] == sauce.lower()) &
                (df_mod[mod_name_col].str.contains("choose your spread"))
            ]
            qty = float(match[qty_col].values[0]) if not match.empty else 0
            if qty != 0:
                result[sauce.lower()] = qty

        # Add-ons (Eggs, Mushroom, Pickles, Sriracha): only include where modifier name contains "Choose your Add-Ons"
        egg1 = df_mod[
            (df_mod[mod_option_col] == "boileg egg") &
            (df_mod[mod_name_col].str.contains("choose your add-ons"))
        ][qty_col].sum()
        egg2 = df_mod[
            (df_mod[mod_option_col] == "scrambled egg") &
            (df_mod[mod_name_col].str.contains("choose your add-ons"))
        ][qty_col].sum()
        egg_total = egg1 + egg2
        if egg_total != 0:
            result["egg"] = egg_total

        for opt in ["Mushroom", "Pickles", "Sriracha"]:
            match = df_mod[
                (df_mod[mod_option_col] == opt.lower()) &
                (df_mod[mod_name_col].str.contains("choose your add-ons"))
            ]
            qty = float(match[qty_col].values[0]) if not match.empty else 0
            if qty != 0:
                result[opt.lower()] = qty
        print(f"Branch selected: {branch}")
        if branch.lower() == "chmm":
            print("Branch is CHMM, looking for 'Water CHMM'")
            print("Modifier options available:", df_mod[mod_option_col].unique())
            qty = get_qty("Water CHMM")
            if qty != 0:
                result["water"] = qty
                result["water chmm"] = qty
        else:
            qty = get_qty("Water")
            if qty != 0:
                result["water"] = qty

        # Coffee based on option names
        for coffee in [
            "Hot Americano", "Hot Latte", "Hot Cappuccino", "Hot Caramel Macchiato",
            "Iced Americano", "Iced Latte", "Iced Cappuccino", "Iced Caramel Macchiato"
        ]:
            qty = get_qty(coffee)
            if qty != 0:
                result[coffee.lower()] = qty

        # Smoothies / Detox drinks
        for drink in ["Golden Boost", "Green Detox", "Pink Glow"]:
            qty = get_qty_if_contains(drink, "smoothies")
            if qty != 0:
                result[drink.lower()] = qty

        # Softdrinks
        softdrink_total = get_qty("Coke Regular") + get_qty("Coke Zero") + get_qty("Sprite")
        if softdrink_total != 0:
            result["softdrinks"] = softdrink_total

        # Handle missing spreads (modifier name should include "choose your spread")
        for spread in ["Marinara", "Strawberry Jam", "Peanut Butter"]:
            match = df_mod[
                (df_mod[mod_option_col] == spread.lower()) &
                (df_mod[mod_name_col].str.contains("choose your spread"))
            ]
            qty = float(match[qty_col].values[0]) if not match.empty else 0
            if qty != 0:
                result[spread.lower()] = qty

        # Handle pineapple under 'Choose your Add-Ons'
        match = df_mod[
            (df_mod[mod_option_col] == "pineapple") &
            (df_mod[mod_name_col].str.contains("choose your add-ons"))
        ]
        qty = float(match[qty_col].values[0]) if not match.empty else 0
        if qty != 0:
            result["pineapple"] = qty

        # Salad-specific sauces (sum all quantities where modifier name contains 'salad')
        for salad_sauce in ["Balsamic Vinaigrette", "Garlic Ranch", "Honey Mustard"]:
            mask = (
                (df_mod[mod_option_col] == salad_sauce.lower()) &
                (df_mod[mod_name_col].str.contains("salad"))
            )
            qty = df_mod.loc[mask, qty_col].sum()
            if qty != 0:
                result[f"salad - {salad_sauce.lower()}"] = qty

        print("DEBUG: Final water value →", result.get("water"))
        print("DEBUG: All option names containing 'water':")
        print(df_mod[df_mod[mod_option_col].str.contains("water")][[mod_option_col, qty_col]])
    return result

    # --- MODIFIER FILE: Special Salad Garlic Ranch logic ---
    # Only execute if modifier_file is provided
    if modifier_file is not None:
        if modifier_file.name.endswith(".csv"):
            modifier_file.seek(0)
            df_mod = pd.read_csv(modifier_file)
        else:
            df_mod = pd.read_excel(modifier_file)
        # Normalize columns
        df_mod.columns = [col.strip().lower() for col in df_mod.columns]
        # Special rule: Garlic Ranch used in Salad
        salad_ranch = df_mod[
            (df_mod["option_name"].str.lower() == "garlic ranch") &
            (df_mod["modifier_name"].str.lower().str.contains("salad"))
        ]
        if not salad_ranch.empty:
            salad_ranch_val = salad_ranch["quantity_sold"].sum()
            try:
                result["salad:garlic ranch"] = float(str(salad_ranch_val).replace(",", ""))
            except:
                pass