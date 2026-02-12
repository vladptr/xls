from modules.database import supabase

def calculate_level(exp):
    if exp < 125:  # 1-5 уровни по 25
        return exp // 25 + 1
    elif exp < 375:  # 6-10 уровни по 50
        return 5 + (exp - 125) // 50 + 1
    elif exp < 1875:  # 11-25 уровни по 100
        return 10 + (exp - 375) // 100 + 1
    else:  # 26+
        return 25 + (exp - 1875) // 150 + 1

def get_next_level_exp(level: int) -> int:
    if level < 5:
        return 25 * level
    elif level < 10:
        return 125 + 50 * (level - 5)
    elif level < 25:
        return 375 + 100 * (level - 10)
    else:
        return 1875 + 150 * (level - 25)

def calculate_level_from_exp(exp):
    level = 1
    while True:
        need = get_next_level_exp(level)
        if exp < need:
            break
        exp -= need
        level += 1
    return level, exp, get_next_level_exp(level)

def get_total_exp_before(level):
    total = 0
    for l in range(1, level):
        total += get_next_level_exp(l)
    return total

def update_experience(user_id, added_exp):
    row = supabase.table("user_levels").select("*").eq("user_id", user_id).limit(1).execute()
    if row.data:
        exp = row.data[0]["exp"] + added_exp
        level = calculate_level(exp)
        supabase.table("user_levels").update({"exp": exp, "level": level}).eq("user_id", user_id).execute()
    else:
        supabase.table("user_levels").insert({
            "user_id": user_id,
            "exp": added_exp,
            "level": calculate_level(added_exp)
        }).execute()

