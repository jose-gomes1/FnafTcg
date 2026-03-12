"""FNAF TCG - Ability System"""
import random
from engine.cards import AnimatronicCard, ElectricityCard, FNAF3_NAMES

def _roll(): return random.randint(1,6)

def reroll_die(attacker, player_active):
    """
    Roll a d6. If the result is a failure (odd), check if the attacker
    or any ally in player_active has the reroll passive (Shadow Freddy or
    Funtime Endo) and it hasn't been used this turn.
    Returns the final roll after any reroll.
    """
    from ui.cli import yes_no
    roll = _roll()
    rerollers = {"Shadow Freddy", "Funtime Endo"}
    has_reroller = next(
        (a for a in [attacker] + player_active
         if a.name in rerollers and a.passive_active() and not a._reroll_used),
        None
    )
    if roll % 2 != 0 and has_reroller:
        print(f"  [{has_reroller.name}] Dado: {roll} — falhou! Podes relançar.")
        if yes_no("  Usar relançamento de dado?"):
            has_reroller._reroll_used = True
            roll = _roll()
            print(f"  Novo dado: {roll}")
    return roll


def calc_damage(raw, attacker, target, atk_party, tgt_party):
    dmg = raw
    if "Nightmare" in target.name and any(a.name=="Nightmare Foxy" and a.passive_active() for a in tgt_party):
        dmg = dmg // 2
    if "Withered" in target.name and any(a.name=="Withered Bonnie" and a.passive_active() for a in tgt_party):
        dmg = max(0, dmg - 30)
    if target.name == "Toy Foxy (Mangle)" and "Foxy" in attacker.name:
        dmg *= 2
    if "Nightmare" in attacker.name and any(a.name=="Plushtrap" and a._double_damage_turn and a.passive_active() for a in atk_party):
        dmg *= 2
    if attacker.name == "Springtrap" and attacker.passive_active():
        dmg += sum(1 for a in atk_party if "Phantom" in a.name) * 10
    return dmg

def extra_elec_cost(opp_party):
    return sum(1 for a in opp_party if a.name=="Phantom Mangle" and a.passive_active())

def can_suppress(card, opp_party):
    return ("Nightmare" not in card.name and
            any(a.name=="Nightmare Freddy" and a.passive_active() for a in opp_party))

def get_max_party(player):
    wgf = next((a for a in player.active if a.name=="Withered Golden Freddy" and a.passive_active()), None)
    if wgf and sum(1 for a in player.active if "Withered" in a.name) > 1:
        return 6
    return 4

def on_enter(card, game, player_idx):
    from ui.cli import pick_index
    player = game.players[player_idx]
    opponent = game.players[1-player_idx]
    if not card.passive_active(): return
    if card.name == "Phantom Foxy":
        alive = opponent.alive_active()
        if alive:
            idx = pick_index("[Phantom Foxy] Entrada: 20 dano em qual animatronic?", alive)
            alive[idx].take_damage(20, card)
            game.log(f"  Phantom Foxy entra: 20 dano em {alive[idx].name}!")
    elif card.name == "Nightmare Chica":
        alive = opponent.alive_active()
        stalled = []
        for i in range(min(2, len(alive))):
            rem = [a for a in alive if a not in stalled]
            if not rem: break
            idx = pick_index(f"[Nightmare Chica] Stall {i+1}/2:", rem)
            t = rem[idx]
            if t.name not in ("Nightmare Fredbear","Nightmare"):
                t.stalled_turns += 1; stalled.append(t)
                game.log(f"  {t.name} em stall!")
            else:
                game.log(f"  {t.name} e imune a stall de habilidades!")
    elif card.name == "Plushtrap":
        card._double_damage_turn = True
        game.log(f"  Plushtrap entra - Nightmares dao 2x dano este turno!")

def on_death(card, game, owner_idx):
    from ui.cli import pick_index
    from engine.cards import AnimatronicCard as AC
    player = game.players[owner_idx]
    opponent = game.players[1-owner_idx]
    if not card.passive_active(): return False
    if card.name == "Phantom Puppet":
        alive = opponent.alive_active()
        stalled = []
        for i in range(min(2, len(alive))):
            rem = [a for a in alive if a not in stalled]
            if not rem: break
            idx = pick_index(f"[Phantom Puppet] Stall {i+1}/2:", rem)
            rem[idx].stalled_turns += 2; stalled.append(rem[idx])
            game.log(f"  Phantom Puppet: {rem[idx].name} em stall por 2 turnos!")
        return False
    if card.name == "Endo-02" and not card.has_survived_once:
        roll = _roll()
        game.log(f"  [Endo-02] Dado revive: {roll} - {'PAR - revive!' if roll%2==0 else 'impar.'}")
        if roll % 2 == 0:
            card.current_hp = 50; card.has_survived_once = True
            if card not in player.active: player.active.append(card)
            return True
        return False
    if card.name == "Plush Endo" and card._last_attacker:
        atk = card._last_attacker
        if atk and atk.is_alive():
            atk.take_damage(card.max_hp, None)
            game.log(f"  Plush Endo reflete dano em {atk.name}!")
        return False
    if card.name == "Springbonnie" and not card.springbonnie_transformed:
        trap_in_deck = [c for c in player.deck if isinstance(c,AC) and c.name.endswith("trap")]
        if trap_in_deck:
            idx = pick_index("[Springbonnie] Transformar em qual 'trap'?", trap_in_deck)
            chosen = trap_in_deck[idx]
            player.deck.remove(chosen); chosen.electricity = 0
            random.shuffle(player.deck)
            if card in player.active:
                pos = player.active.index(card)
                player.active[pos] = chosen
                card.springbonnie_transformed = True
                game.log(f"  Springbonnie transforma-se em {chosen.name} (sem ponto)!")
                on_enter(chosen, game, owner_idx)
                return True
        else:
            game.log("  Nenhum animatronic 'trap' no deck.")
    return False

def start_of_turn_passives(player, game, player_idx):
    extra = set()
    for a in player.active:
        if a.name == "Springlock Endo" and a.passive_active():
            roll = _roll()
            game.log(f"  [Springlock Endo] Dado: {roll} - {'par! Fnaf3 atacam 1x a mais.' if roll%2==0 else 'impar.'}")
            if roll % 2 == 0:
                for c in player.active:
                    if c.name in FNAF3_NAMES: extra.add(id(c))
    return extra

def end_of_turn_passives(player, game, player_idx):
    for a in player.active:
        if a.name == "Endo-01" and a.passive_active() and a._endo01_rust_target:
            tgt = a._endo01_rust_target
            if tgt and tgt.is_alive():
                tgt.take_damage(10)
                game.log(f"  Ferrugem Endo-01: {tgt.name} perde 10 HP!")
            a._endo01_rust_target = None

def use_active_ability(card, game, player_idx):
    from ui.cli import pick_index, yes_no
    from engine.cards import AnimatronicCard as AC
    player = game.players[player_idx]
    opponent = game.players[1-player_idx]
    if not card.ability_available():
        game.log("Habilidade nao disponivel (ja usada, anulada ou bloqueada).")
        return False
    if can_suppress(card, opponent.active):
        game.log(f"Nightmare Freddy suprime a habilidade de {card.name}!")
        return False
    name = card.name

    if name in ("Freddy","Withered Freddy"):
        e = next((c for c in player.deck if isinstance(c,ElectricityCard)), None)
        if not e or card.electricity >= card.max_electricity:
            game.log("Impossivel: sem eletricidade no deck ou maximo atingido.")
            return False
        player.deck.remove(e); random.shuffle(player.deck)
        card.electricity += 1
        game.log(f"{name} busca 1 eletricidade do deck!")

    elif name == "Chica":
        chicas = [a for a in player.active if "Chica" in a.name]
        if not chicas: game.log("Nenhuma Chica na party."); return False
        idx = pick_index("Curar qual Chica? (+10 HP)", chicas)
        chicas[idx].heal(10); game.log(f"Chica cura 10 HP em {chicas[idx].name}!")

    elif name == "Foxy":
        alive = opponent.alive_active()
        if not alive: return False
        idx = pick_index("Foxy: 5 dano em qual animatronic?", alive)
        alive[idx].take_damage(5, card)
        game.log(f"Foxy: 5 dano em {alive[idx].name}!")

    elif name == "Golden Freddy":
        alive = opponent.alive_active()
        if not alive: return False
        idx = pick_index("Stall em qual animatronic?", alive)
        t = alive[idx]
        if t.name in ("Nightmare Fredbear","Nightmare") and t.passive_active():
            game.log(f"{t.name} e imune a stall de habilidades!"); return False
        t.stalled_turns += 1
        game.log(f"Golden Freddy: {t.name} em stall por 1 turno!")

    elif name == "Toy Bonnie":
        targets = [a for a in opponent.alive_active() if a.electricity > 0]
        if not targets: game.log("Oponente sem eletricidade."); return False
        idx = pick_index("Descartar eletricidade de qual?", targets)
        targets[idx].electricity -= 1
        game.log(f"Toy Bonnie descarta 1 eletricidade de {targets[idx].name}!")

    elif name == "Toy Chica":
        for a in player.active: a._redirecting = False
        card._redirecting = True
        game.log("Toy Chica ativa Provocacao!")

    elif name == "Puppet":
        if not player.active: return False
        idx = pick_index("Proteger qual animatronic?", player.active)
        player.active[idx]._puppet_protected = True
        game.log(f"Puppet protege {player.active[idx].name} contra proximo ataque fatal!")

    elif name == "Balloon Boy":
        alive = opponent.alive_active()
        if not alive: return False
        for a in alive: a.take_damage(10, card)
        game.log("Balloon Boy: 10 dano em toda a party do oponente!")

    elif name in ("JJ","Phantom Freddy"):
        own = player.alive_active(); opp_alive = opponent.alive_active()
        if not opp_alive: return False
        healed = 0
        for a in own:
            h = min(40-healed, a.max_hp-a.current_hp)
            a.current_hp += h; healed += h
            if healed >= 40: break
        remaining = 40
        for a in opp_alive:
            if remaining <= 0: break
            d = min(remaining, a.current_hp)
            a.take_damage(d, card); remaining -= d
        game.log(f"{name}: move 40 dano da sua party para a party do oponente!")

    elif name == "RWQFSFASXC":
        e = next((c for c in player.hand if isinstance(c,ElectricityCard)), None)
        if not e: game.log("Sem eletricidade na mao para descartar."); return False
        targets = [a for a in opponent.alive_active() if a.ability_type]
        if not targets: game.log("Oponente sem animatronics com habilidade."); return False
        idx = pick_index("Anular habilidade de qual animatronic?", targets)
        targets[idx].ability_nullified_turns = 2
        player.hand.remove(e); player.discard.append(e)
        game.log(f"RWQFSFASXC anula habilidade de {targets[idx].name} por 2 turnos!")

    elif name == "Phantom Chica":
        alive = opponent.alive_active()
        if not alive: return False
        idx = pick_index("[Phantom Chica] Bloquear ataques de qual animatronic?", alive)
        card.phantom_chica_locked = alive[idx]
        game.log(f"Phantom Chica: {alive[idx].name} so pode usar Single Target!")

    elif name == "Phantom Balloon Boy":
        roll = _roll()
        game.log(f"  [Phantom BB] Dado: {roll}")
        if roll % 2 == 0:
            targets = [a for a in opponent.alive_active() if a.electricity > 0]
            if targets:
                idx = pick_index("Par! Descartar eletricidade de qual?", targets)
                targets[idx].electricity -= 1
                game.log(f"  1 eletricidade descartada de {targets[idx].name}!")
        else:
            game.log("  Impar! Cada animatronic da party perde 1 eletricidade.")
            for a in player.active:
                if a.electricity > 0: a.electricity -= 1

    elif name in ("Jack-O-Bonnie","Jack-O-Chica","Nightmare Mangle","Nightmare Balloon Boy"):
        e_list = [c for c in player.discard if isinstance(c,ElectricityCard)]
        if not e_list: game.log("Sem eletricidade no descarte."); return False
        if card.electricity >= card.max_electricity: game.log(f"{name} ja tem o maximo de eletricidade."); return False
        player.discard.remove(e_list[0]); card.electricity += 1
        game.log(f"{name} recupera 1 eletricidade do descarte!")

    elif name == "Nightmarionne":
        alive = opponent.alive_active()
        if not alive: return False
        idx = pick_index("Nightmarionne: 20 dano em qual?", alive)
        alive[idx].take_damage(20, card)
        game.log(f"Nightmarionne: 20 dano em {alive[idx].name}!")

    elif name == "The Mimic (M2)":
        all_play = [a for a in player.active+opponent.active if a.ability_type and a.name!="The Mimic (M2)"]
        if not all_play: game.log("Nenhuma habilidade para copiar."); return False
        idx = pick_index("Copiar habilidade de qual animatronic?", all_play)
        source = all_play[idx]
        game.log(f"The Mimic copia '{source.ability_name}' de {source.name}!")
        saved = (card.name,card.ability_name,card.ability_type,card.ability_desc)
        card.name=source.name; card.ability_name=source.ability_name
        card.ability_type=source.ability_type; card.ability_desc=source.ability_desc
        result = use_active_ability(card, game, player_idx)
        card.name,card.ability_name,card.ability_type,card.ability_desc = saved
        card.ability_used_this_turn = True
        return result
    else:
        game.log(f"Habilidade ativa de '{name}' nao implementada.")
        return False

    card.ability_used_this_turn = True
    game._check_win_conditions()
    return True