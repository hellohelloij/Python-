import time
from datetime import datetime

TAX_RATE = 0.10
DEFAULT_MENU = {
    'Cheeseburger': {
        'price': 4.99, 'category': 'burger',
        'allergens': ['dairy', 'gluten'], 'gluten_free_available': False
    },
    'Double Cheeseburger': {
        'price': 5.50, 'category': 'burger',
        'allergens': ['dairy', 'gluten'], 'gluten_free_available': True
    },
    'The Clogger': {
        'price': 6.70, 'category': 'burger',
        'allergens': ['gluten'], 'gluten_free_available': False
    }
}
DEFAULT_TOPPINGS = {
    'Bacon': 0.75,
    'Extra Cheese': 0.50,
    'Onion Rings': 1.00,
    'GlutenFreeBun': 1.50
}
DEFAULT_INVENTORY = {
    'Cheeseburger_patty': 20,
    'Double_patty': 15,
    'Bun': 30,
    'GlutenFreeBun': 10,
    'Bacon': 20,
    'Extra Cheese': 30,
    'Onion Rings': 15,
    'Fries+Drink': 10
}
beef_burgers = DEFAULT_MENU.copy()
toppings = DEFAULT_TOPPINGS.copy()
inventory = DEFAULT_INVENTORY.copy()
LOYALTY_DB = {}
ordered_items = []
loyalty_id = None

def get_valid_int(prompt, allow_zero=False):
    while True:
        s = input(prompt).strip()
        if s.isdigit():
            v = int(s)
            if allow_zero and v >= 0:
                return v
            if not allow_zero and v > 0:
                return v
        if allow_zero:
            print("Please enter a whole number (0 or more).")
        else:
            print("Please enter a whole number greater than 0.")

def get_choice(prompt, choices):
    choices_up = [c.upper() for c in choices]
    while True:
        c = input(prompt).strip().upper()
        if c in choices_up:
            return c
        print("Invalid choice. Try:", "/".join(choices))

def format_currency(x):
    return f"${x:.2f}"

def generate_order_no():
    return int(time.time() % 1000000)

def generate_pickup_code(order_no):
    code = f"BBG-{order_no}-{int(time.time())%10000}"
    fname = f"pickup_{order_no}.txt"
    with open(fname, 'w') as f:
        f.write(code)
    return code, fname

def recipe_ingredients(item_name, qty, toppings_list, gf_flag):
    req = {}
    if 'Double' in item_name:
        req['Double_patty'] = qty
    else:
        req['Cheeseburger_patty'] = qty
    if gf_flag:
        req['GlutenFreeBun'] = qty
    else:
        req['Bun'] = qty
    for t in toppings_list:
        key = t
        req[key] = req.get(key, 0) + qty
    return req

def chkinvresv(item_name, qty, toppings_list, gf_flag):
    required = recipe_ingredients(item_name, qty, toppings_list, gf_flag)
    for ingredient, need in required.items():
        have = inventory.get(ingredient, 0)
        if have < need:
            return False, ingredient
    for ingredient, need in required.items():
        inventory[ingredient] = inventory.get(ingredient, 0) - need
    return True, None

def restore_inventory_for(entry):
    required = recipe_ingredients(entry['name'], entry['qty'], entry['toppings'], entry['GF'])
    for ingredient, need in required.items():
        inventory[ingredient] = inventory.get(ingredient, 0) + need

def adjust_inventory_for_quantity_change(entry, new_qty):
    old_qty = entry['qty']
    diff = new_qty - old_qty
    if diff == 0:
        return True, None
    if diff > 0:
        ok, missing = chkinvresv(entry['name'], diff, entry['toppings'], entry['GF'])
        if not ok:
            return False, missing
        return True, None
    else:
        restore_entry = {'name': entry['name'], 'qty': -diff, 'toppings': entry['toppings'], 'GF': entry['GF']}
        restore_inventory_for(restore_entry)
        return True, None

def menu():
    print("\n--- Beef Burger Menu ---")
    i = 1
    names = list(beef_burgers.keys())
    for name in names:
        info = beef_burgers[name]
        gf = " (GF Available)" if info.get('gluten_free_available') else ""
        allergy = ", ".join(info.get('allergens', []))
        print(f"{i}. {name}{gf} - {format_currency(info['price'])}  Allergens: {allergy}")
        i += 1
    print("T. Show Toppings & Prices")
    print("R. Remove / Edit cart")
    print("L. Loyalty / Enter ID")
    print("C. Checkout")
    print("Q. Quit")

def show_toppings():
    print("\n--- Toppings & Extra Options ---")
    for t, p in toppings.items():
        print(f"- {t}: {format_currency(p)}")
    print()

def cart_subtotal():
    return sum(e['qty'] * e['unit_price'] for e in ordered_items)

def show_cart():
    if not ordered_items:
        print("\nYour cart is empty.")
        return
    print("\n--- Your Cart ---")
    for idx, e in enumerate(ordered_items, start=1):
        tops = ", ".join(e['toppings']) if e['toppings'] else "No extras"
        gf = " GF" if e['GF'] else ""
        line_total = e['qty'] * e['unit_price']
        print(f"{idx}. {e['qty']} x {e['name']}{gf} @ {format_currency(e['unit_price'])} ea - {format_currency(line_total)} | {tops}")
    print(f"Cart subtotal: {format_currency(cart_subtotal())}")

def edit_cart():
    show_cart()
    if not ordered_items:
        return
    idx = get_valid_int("Enter item # to edit (0 to cancel): ", allow_zero=True)
    if idx == 0:
        return
    if idx < 1 or idx > len(ordered_items):
        print("Invalid index.")
        return
    entry = ordered_items[idx - 1]
    print("1. Change quantity")
    print("2. Remove item")
    choice = get_choice("Choose (1/2): ", ['1','2'])
    if choice == '2':
        restore_inventory_for(entry)
        ordered_items.pop(idx - 1)
        print("Item removed.")
    else:
        new_qty = get_valid_int("New quantity: ", allow_zero=False)
        ok, missing = adjust_inventory_for_quantity_change(entry, new_qty)
        if not ok:
            print(f"Cannot change quantity: insufficient {missing}.")
            return
        entry['qty'] = new_qty
        print("Quantity updated.")

def add_item_flow(item_num):
    names = list(beef_burgers.keys())
    if item_num < 1 or item_num > len(names):
        print("Invalid item number.")
        return
    name = names[item_num - 1]
    base_price = beef_burgers[name]['price']
    qty = get_valid_int("Quantity: ")
    gf_flag = False
    if beef_burgers[name].get('gluten_free_available'):
        gf_choice = get_choice("Gluten-free bun? (Y/N): ", ['Y','N'])
        if gf_choice == 'Y':
            gf_flag = True
            base_price += toppings.get('GlutenFreeBun', 0.0)
    chosen_toppings = []
    show_toppings()
    while True:
        t = input("Add topping name or press Enter to finish: ").strip()
        if t == "":
            break
        if t in toppings:
            chosen_toppings.append(t)
            base_price += toppings[t]
            print(f"Added {t}.")
        else:
            print("Invalid topping name. Try again or press Enter to finish.")
    notes = input("Any notes (e.g., no onion)? Press Enter to skip: ").strip()
    ok, missing = chkinvresv(name, qty, chosen_toppings, gf_flag)
    if not ok:
        print(f"Sorry, insufficient {missing}. Try smaller qty or different item.")
        return
    entry = {
        'name': name,
        'qty': qty,
        'unit_price': round(base_price, 2),
        'toppings': chosen_toppings,
        'GF': gf_flag,
        'notes': notes
    }
    ordered_items.append(entry)
    print(f"Added {qty} x {name} to cart.")
    burger_list = [k for k,v in beef_burgers.items() if v.get('category') == 'burger']
    if any(e['name'] in burger_list for e in ordered_items):
        upsell = get_choice("Deal suggestion: Add Fries + Drink for $3 extra (Y/N)? ", ['Y','N'])
        if upsell == 'Y':
            if inventory.get('Fries+Drink', 0) > 0:
                inventory['Fries+Drink'] -= 1
                ordered_items.append({'name': 'Fries+Drink', 'qty': 1, 'unit_price': 3.00, 'toppings': [], 'GF': False, 'notes': 'Meal deal'})
                print("Fries+Drink added as meal deal.")
            else:
                print("Sorry, Fries+Drink is out of stock.")

def compute_pair_savings(pairs):
    burger_prices = []
    for e in ordered_items:
        if beef_burgers.get(e['name'], {}).get('category') == 'burger':
            burger_prices.extend([e['unit_price']] * e['qty'])
    burger_prices.sort()
    savings = 0.0
    for i in range(pairs):
        if len(burger_prices) >= 2:
            p1 = burger_prices.pop(0)
            p2 = burger_prices.pop(0)
            normal = p1 + p2
            savings += max(0.0, normal - 10.0)
    return savings

def apply_specials_and_bundles(subtotal):
    burger_qty = sum(e['qty'] for e in ordered_items if beef_burgers.get(e['name'],{}).get('category') == 'burger')
    pairs = burger_qty // 2
    if pairs > 0:
        savings = compute_pair_savings(pairs)
        subtotal -= savings
    return subtotal

def handle_loyalty_and_discounts(subtotal):
    discount = 0.0
    global loyalty_id
    code = input("Discount code (press Enter to skip): ").strip()
    if code:
        if code.upper() == "DISCOUNT10":
            discount += 0.10 * subtotal
            print("10% discount code applied.")
        else:
            print("Invalid discount code. No discount applied.")
    if loyalty_id:
        points = LOYALTY_DB.get(loyalty_id, 0)
        print(f"Loyalty points: {points}")
        if points >= 100:
            use = get_choice("Redeem 100 points for $5 off? (Y/N): ", ['Y','N'])
            if use == 'Y':
                discount += 5.0
                LOYALTY_DB[loyalty_id] = points - 100
                print("100 points redeemed for $5 off.")
    return discount

def checkout():
    global ordered_items, loyalty_id
    if not ordered_items:
        print("Cart empty. Returning to menu.")
        return
    subtotal = cart_subtotal()
    subtotal = apply_specials_and_bundles(subtotal)
    discount = handle_loyalty_and_discounts(subtotal)
    tax = subtotal * TAX_RATE
    total = subtotal - discount + tax
    print("\n--- RECEIPT PREVIEW ---")
    show_cart()
    print(f"SUBTOTAL: {format_currency(subtotal)}")
    if discount > 0:
        print(f"DISCOUNT: -{format_currency(discount)}")
    print(f"TAX: {format_currency(tax)}")
    print(f"TOTAL: {format_currency(total)}")
    confirm = get_choice("Confirm & Pay? (P = pay / R = edit): ", ['P','R'])
    if confirm == 'R':
        edit_cart()
        return
    order_no = generate_order_no()
    code, fname = generate_pickup_code(order_no)
    if loyalty_id:
        earned = int(total)
        LOYALTY_DB[loyalty_id] = LOYALTY_DB.get(loyalty_id, 0) + earned
        print(f"Earned {earned} loyalty points. Total: {LOYALTY_DB[loyalty_id]}")
    print(f"Order #{order_no} paid. Pickup code: {code} (saved to {fname})")
    ordered_items = []

def main():
    global loyalty_id
    print("Welcome to the Beef Burger Co. menu!")
    while True:
        menu()
        action = input("Enter item # or action: ").strip()
        if action == '':
            continue
        if action.upper() == 'T':
            show_toppings()
            continue
        if action.upper() in ('R', 'E'):
            edit_cart()
            continue
        if action.upper() == 'L':
            lid = input("Enter loyalty ID (or press Enter to skip / new ID): ").strip()
            if lid == '':
                loyalty_id = None
            else:
                loyalty_id = lid
                if lid not in LOYALTY_DB:
                    LOYALTY_DB[lid] = 0
                print(f"Loyalty ID set: {loyalty_id}")
            continue
        if action.upper() == 'C':
            checkout()
            continue
        if action.upper() == 'Q':
            print("Exiting. Goodbye!")
            break
        try:
            item_num = int(action)
            add_item_flow(item_num)
        except ValueError:
            print("Invalid input. Try again.")
if __name__ == '__main__':
    main()
