"""FNAF TCG - Combat Resolution"""
import random
from engine.abilities import calc_damage, extra_elec_cost, reroll_die

def resolve_attack(attacker, attack, targets, player_active, opponent_active, game=None):
    from ui.cli import pick_index, yes_no
    logs = []
    if not attacker.can_attack():
        logs.append(f"{attacker.name} esta em stall e nao pode atacar!"); return logs
    extra = extra_elec_cost(opponent_active)
    total_cost = attack.cost + extra
    if extra > 0: logs.append(f"  (Phantom Mangle: +{extra} elec, total {total_cost})")
    if not attacker.spend_electricity(total_cost):
        logs.append(f"{attacker.name} nao tem eletricidade suficiente ({total_cost} necessario)."); return logs
    t_type = attack.attack_type.strip().lower()
    a_name = attack.name
    taunt = next((a for a in opponent_active if a._redirecting), None)
    if taunt and t_type in ("single","multi","stall"):
        targets = [taunt]
        logs.append(f"  Provocacao! Ataque redirecionado para {taunt.name}!")
    for opp in opponent_active:
        if (opp.name=="Phantom Chica" and opp.passive_active()
                and opp.phantom_chica_locked is attacker and t_type=="multi"):
            logs.append(f"  Phantom Chica bloqueia {attacker.name} - so pode usar Single Target!")
            attacker.electricity += total_cost; return logs
    def mask(t):
        return (getattr(t,"_freddy_mask",False)
                and ("Toy" in attacker.name or "Withered" in attacker.name)
                and attacker.name != "Withered Foxy")
    if t_type == "single":
        if not targets: logs.append("Nenhum alvo."); return logs
        t = targets[0]
        if mask(t): logs.append(f"Freddy Mask bloqueia o ataque em {t.name}!"); t._freddy_mask=False; return logs
        dmg = calc_damage(attack.value, attacker, t, player_active, opponent_active)
        t.take_damage(dmg, attacker)
        logs.append(f"{attacker.name} usa {a_name} em {t.name} - {dmg} dano!")
        if a_name in ("Unscrew","Unscrew 2"):
            roll = reroll_die(attacker, player_active)
            logs.append(f"  Dado {a_name}: {roll} - {'PAR!' if roll%2==0 else 'impar - sem efeito.'}")
            if roll % 2 != 0:
                t.current_hp = min(t.max_hp, t.current_hp+dmg)
                logs.append(f"  Dano anulado.")
        elif a_name == "Controlled Shock":
            t._ability_blocked_turns = max(t._ability_blocked_turns, 1)
            logs.append(f"  {t.name} nao pode usar habilidades no proximo turno!")
        elif a_name == "Sonic Echo":
            t._damage_reduction = max(t._damage_reduction, 50); t._sonic_echo_turns = 2
            logs.append(f"  {t.name}: dano reduzido em 50 por 2 turnos!")
        elif a_name == "Waterhose" and game:
            roll = reroll_die(attacker, player_active)
            logs.append(f"  Waterhose dado: {roll}")
            if roll % 2 == 0:
                half_tgts = [x for x in opponent_active if x.is_alive() and x.current_hp <= x.max_hp//2]
                if half_tgts:
                    idx = pick_index("Par - KO qual animatronic (<=metade HP)?", half_tgts)
                    half_tgts[idx].current_hp = 0; logs.append(f"  {half_tgts[idx].name} reduzido a 0!")
                else: logs.append("  Nenhum alvo com <=metade do HP.")
            else:
                attacker.take_damage(70); logs.append(f"  Nightmare Chica perde 70 HP!")
        elif a_name == "Strings Attached" and game:
            opp_atks = [(a,atk) for a in opponent_active for atk in a.attacks]
            if opp_atks:
                labels = [f"{a.name}: {atk.name}" for a,atk in opp_atks]
                idx = pick_index("Strings Attached - copiar qual ataque?", labels)
                _,copied = opp_atks[idx]
                logs.append(f"  Copia {copied.name}!")
                sub = resolve_attack(attacker, copied, [t], player_active, opponent_active, game)
                attacker.electricity += copied.cost; logs.extend(sub)
            t.stalled_turns += 1; logs.append(f"  {t.name} em stall no proximo turno!")
        elif a_name == "Copycat" and game:
            singles = [(a,atk) for a in opponent_active for atk in a.attacks if atk.attack_type.strip().lower()=="single"]
            if singles:
                labels = [f"{a.name}: {atk.name}" for a,atk in singles]
                idx = pick_index("Copycat - usar qual Single?", labels)
                _,copied = singles[idx]
                sub = resolve_attack(attacker, copied, targets, player_active, opponent_active, game)
                attacker.electricity += copied.cost; logs.extend(sub)
        elif a_name == "Prize Ball" and game:
            opp_atks = [(a,atk) for a in opponent_active for atk in a.attacks]
            if opp_atks:
                labels = [f"{a.name}: {atk.name}" for a,atk in opp_atks]
                idx = pick_index("Prize Ball - usar qual ataque?", labels)
                _,copied = opp_atks[idx]
                sub = resolve_attack(attacker, copied, targets, player_active, opponent_active, game)
                attacker.electricity += copied.cost; logs.extend(sub)
    elif t_type == "multi":
        if not targets: logs.append("Nenhum alvo para Multi Target."); return logs
        if a_name == "ESC Key":
            roll = reroll_die(attacker, player_active)
            logs.append(f"  Dado ESC Key: {roll} - {'impar - sem efeito!' if roll%2!=0 else 'par!'}")
            if roll%2!=0: attacker.electricity+=total_cost; return logs
        elif a_name in ("Tiger's Rock","Tigers Rock"):
            roll = reroll_die(attacker, player_active)
            logs.append(f"  Dado Tigers Rock: {roll} - {'impar - sem efeito!' if roll%2!=0 else ''}")
            if roll%2!=0: attacker.electricity+=total_cost; return logs
        elif a_name == "Slasher":
            rolls = [random.randint(1,6) for _ in range(4)]
            even = sum(1 for r in rolls if r%2==0)
            logs.append(f"  Slasher dados: {rolls} - {even} pares {'(>=3 KO!)' if even>=3 else '(<3 sem efeito)'}")
            if even >= 3:
                for t in targets:
                    if not mask(t): t.current_hp=0; logs.append(f"  {t.name} -> 0 HP!")
            return logs
        elif a_name == "4th Wall":
            remaining = 150
            for t in targets:
                if remaining <= 0: break
                d = min(remaining, t.current_hp)
                d2 = calc_damage(d, attacker, t, player_active, opponent_active)
                t.take_damage(d2, attacker); t._last_attacker = attacker
                remaining -= d; logs.append(f"  {t.name} recebe {d2} dano!")
            return logs
        elif a_name == "Unscrew 2":
            rolls = [random.randint(1,6), random.randint(1,6)]
            pairs = sum(1 for r in rolls if r%2==0)
            logs.append(f"  Unscrew 2 dados: {rolls} - {pairs} par(es) -> {pairs} alvo(s).")
            for t in targets[:pairs]:
                if not mask(t):
                    d = calc_damage(attack.value, attacker, t, player_active, opponent_active)
                    t.take_damage(d, attacker); logs.append(f"  {t.name} recebe {d} dano!")
            return logs
        elif a_name == "Rainy Day 2":
            for t in targets: t._rainy_day_bonus = 30
            logs.append("  Rainy Day 2: oponentes tomam +30 no proximo turno!"); return logs
        elif a_name == "Power Song":
            for a in player_active:
                if "Endo" in a.name: a._double_damage_turn = True
            logs.append("  Power Song: Endos dao dobro de dano!"); return logs
        elif a_name == "Neon Wall":
            for a in player_active:
                if "Endo" in a.name: a._damage_reduction=999; a._sonic_echo_turns=1
            logs.append("  Neon Wall: Endos tomam metade de dano!"); return logs
        for t in targets:
            if mask(t): logs.append(f"  Freddy Mask bloqueia {t.name}!"); t._freddy_mask=False; continue
            dmg = calc_damage(attack.value, attacker, t, player_active, opponent_active)
            t.take_damage(dmg, attacker); t._last_attacker = attacker
            logs.append(f"  {t.name} recebe {dmg} dano de {a_name}!")
        if a_name == "Phantom Fog":
            for t in targets:
                t._damage_reduction=max(t._damage_reduction,10); t._sonic_echo_turns=max(t._sonic_echo_turns,1)
            logs.append("  Phantom Fog: oponentes causam -10 dano por 1 turno!")
    elif t_type == "heal":
        wc = any(a.name=="Withered Chica" and a.passive_active() for a in player_active)
        mult = 2 if wc else 1
        heal_targets = targets if targets else player_active
        for t in heal_targets: t.heal(attack.value * mult)
        if len(heal_targets)==1: logs.append(f"{attacker.name} usa {a_name} - cura {attack.value*mult} HP em {heal_targets[0].name}!")
        else: logs.append(f"{attacker.name} usa {a_name} - cura {attack.value*mult} HP na party!")
    elif t_type == "stall":
        if not targets: logs.append("Nenhum alvo para Stall."); return logs
        sv = attack.value if attack.value > 0 else 1
        for t in targets:
            if t.name=="Bonnie" and t.passive_active(): logs.append(f"  Bonnie e imune a Stall de ataques!")
            elif t.name=="Toy Freddy" and t.passive_active(): logs.append(f"  Toy Freddy e imune a Stall de ataques!")
            else:
                t.stalled_turns += sv
                logs.append(f"{attacker.name} usa {a_name} em {t.name} - stall por {sv} turno(s)!")
    else:
        logs.append(f"Tipo desconhecido: {attack.attack_type}")
    return logs