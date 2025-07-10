import pandas as pd

def extract_data(modifier_file, item_file, discount_file, payment_file):
    result = {}

    # --- PAYMENT FILE: Extract negative GCash amount ---
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

    # --- ITEM FILE: Extract sold counts from specific items ---
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
                result[item.lower()] = float(str(val).replace(",", ""))
            except:
                continue

    # --- MODIFIER FILE: Process ingredients and modifiers ---
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
    # DEBUG: print unique option and modifier names
    print("Modifier file options:", df_mod[mod_option_col].unique())
    print("Modifier file modifiers:", df_mod[mod_name_col].unique())

    def get_qty(option):
        match = df_mod[df_mod[mod_option_col] == option.lower()]
        return float(match[qty_col].values[0]) if not match.empty else 0

    def get_qty_if_contains(option, keyword):
        match = df_mod[(df_mod[mod_option_col] == option.lower()) & (df_mod[mod_name_col].str.contains(keyword.lower()))]
        return float(match[qty_col].values[0]) if not match.empty else 0

    # Bread
    for bread in ["Ciabatta", "Brioche", "Multigrain"]:
        result[bread.lower()] = get_qty(bread)

    # Free veggies - match using get_qty with Option Name directly
    print("---- FREE VEGGIES DEBUG ----")
    for veg in ["Cucumber", "Lettuce", "Tomato", "White Onion"]:
        qty = get_qty(veg)
        print(f"{veg}: {qty}")
        if qty:
            result[veg.lower()] = qty
    print("---- END FREE VEGGIES DEBUG ----")

    # Proteins
    for meat in ["Bacon", "Beef Salami", "Ham", "Honey Ham", "Italian Chicken", "Chickpeas", "Tuna Flakes"]:
        result[meat.lower()] = get_qty(meat)

    # Cheese
    for cheese in ["Cheddar", "Mozzarella", "Two Cheese"]:
        result[cheese.lower()] = get_qty(cheese)

    # Sauces
    for sauce in ["Balsamic Vinaigrette", "Cream Cheese & Chive", "Garlic Ranch", "Honey Mustard", "Marinara", "Pesto Cream", "Ultimate Aioli", "Strawberry Jam"]:
        result[sauce.lower()] = get_qty(sauce)

    # Eggs (Boiled + Scrambled)
    egg1 = get_qty("Boileg Egg")
    egg2 = get_qty("Scrambled Egg")
    result["egg"] = egg1 + egg2

    # Others
    for opt in ["Mushroom", "Pickles", "Sriracha", "Pineapple"]:
        result[opt.lower()] = get_qty(opt)
    result["water"] = get_qty("Water")

    # Coffee based on option names
    for coffee in [
        "Hot Americano", "Hot Latte", "Hot Cappuccino", "Hot Caramel Macchiato",
        "Iced Americano", "Iced Latte", "Iced Cappuccino", "Iced Caramel Macchiato"
    ]:
        qty = get_qty(coffee)
        if qty:
            result[coffee.lower()] = qty

    # Softdrinks
    softdrink_total = get_qty("Coke Regular") + get_qty("Coke Zero") + get_qty("Sprite")
    result["softdrinks"] = softdrink_total

    # Salad-specific sauces
    for salad_sauce in ["Balsamic Vinaigrette", "Garlic Ranch", "Honey Mustard"]:
        qty = get_qty_if_contains(salad_sauce, "salad")
        if qty:
            result[f"salad - {salad_sauce.lower()}"] = qty

    print("FINAL RESULT KEYS:", result.keys())
    print("FINAL RESULT VALUES:", result)
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