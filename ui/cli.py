"""FNAF TCG - CLI"""
from engine.cards import AnimatronicCard, SupportCard, ElectricityCard

def pick_index(prompt, items):
    for i,item in enumerate(items): print(f"  [{i}] {item}")
    while True:
        try:
            val = int(input(f"{prompt} (numero): "))
            if 0 <= val < len(items): return val
        except (ValueError, KeyboardInterrupt): pass
        print(f"  Escolhe entre 0 e {len(items)-1}.")

def yes_no(prompt):
    while True:
        r = input(f"{prompt} (s/n): ").strip().lower()
        if r in ("s","sim","y","yes"): return True
        if r in ("n","nao","nao","no"): return False

def pick_animatronic_from_deck(player):
    animatronics = [c for c in player.deck if isinstance(c,AnimatronicCard)]
    if not animatronics: print("  Nenhum animatronic no deck."); return None
    idx = pick_index("Escolhe animatronic do deck:", animatronics)
    chosen = animatronics[idx]; player.deck.remove(chosen)
    from engine.player import MAX_ACTIVE
    if len(player.active) < MAX_ACTIVE: player.active.append(chosen)
    else: player.hand.append(chosen)
    import random; random.shuffle(player.deck)
    return chosen

def display_game_state(game):
    p = game.current_player(); opp = game.opponent()
    print("\n" + "░"*62)
    print(f"  OPONENTE: {opp.name}  |  Pontos: {opp.points}  |  Deck: {len(opp.deck)}")
    print("  Ativos do oponente:")
    for i,a in enumerate(opp.active):
        stall = f" [STALL {a.stalled_turns}t]" if a.stalled_turns>0 else ""
        null = " [NULL]" if a.ability_nullified_turns>0 else ""
        print(f"    [{i}] {a.name}  HP:{a.current_hp}/{a.max_hp}  elec:{a.electricity}{stall}{null}")
    print("░"*62)
    print(f"  {p.name}  |  Pontos: {p.points}  |  Deck: {len(p.deck)}")
    print("  Sua party:")
    for i,a in enumerate(p.active):
        stall = f" [STALL {a.stalled_turns}t]" if a.stalled_turns>0 else ""
        null = " [NULL]" if a.ability_nullified_turns>0 else ""
        prot = " [PROT]" if a._puppet_protected else ""
        extra = " [+ATK]" if game.card_has_extra_attack(a) else ""
        ab = ""
        if a.ability_type=="active": ab=" [HAB OK]" if a.ability_available() else " [HAB usa]"
        elif a.ability_type=="passive": ab=" [PAS]" if a.passive_active() else " [PAS null]"
        print(f"    [{i}] {a.name}  HP:{a.current_hp}/{a.max_hp}  elec:{a.electricity}/{a.max_electricity}{stall}{null}{prot}{extra}{ab}")
    print(f"  Mao ({len(p.hand)} cartas):")
    for i,c in enumerate(p.hand): print(f"    [{i}] {c}")
    print(f"  Eletricidade attachada este turno: {'OK' if p.has_attached_electricity else 'nao'}")
    print("░"*62)

ACTIONS = """
Acoes disponiveis:
  [1] Attchar eletricidade a um animatronic
  [2] Colocar animatronic da mao
  [3] Atacar com um animatronic
  [4] Usar suporte
  [5] Ver detalhes de um animatronic
  [6] Usar habilidade ativa
  [0] Terminar turno
"""

def run_player_turn(game):
    p = game.current_player(); opp = game.opponent()
    attack_counts = {}
    while not game.game_over:
        display_game_state(game)
        print(ACTIONS)
        choice = input("Escolha: ").strip()
        if choice == "0": break

        elif choice == "1":
            if not p.active: print("Nenhum animatronic ativo."); continue
            if p.has_attached_electricity: print("Ja attachaste eletricidade este turno."); continue
            if p.electricity_in_hand()==0: print("Sem eletricidades na mao."); continue
            idx = pick_index("Attchar em qual animatronic?", p.active)
            game.do_attach_electricity(idx)

        elif choice == "2":
            anim = p.animatronics_in_hand()
            if not anim: print("Sem animatronics na mao."); continue
            from engine.abilities import get_max_party
            if len(p.active)>=get_max_party(p): print("Party cheia."); continue
            idx = pick_index("Colocar qual animatronic?", anim)
            game.do_place_animatronic(idx)

        elif choice == "3":
            if game.round==1 and game.turn==game.first_player:
                print("O primeiro jogador nao pode atacar no primeiro turno!"); continue
            alive_pairs = [(i,a) for i,a in enumerate(p.active)
                           if a.can_attack() and attack_counts.get(i,0)<(2 if game.card_has_extra_attack(a) else 1)]
            if not alive_pairs: print("Nenhum animatronic disponivel para atacar."); continue
            display_list = [f"{a.name} (ataques restantes: {(2 if game.card_has_extra_attack(a) else 1)-attack_counts.get(i,0)})" for i,a in alive_pairs]
            pick = pick_index("Atacar com qual animatronic?", display_list)
            a_idx, attacker = alive_pairs[pick]
            if not attacker.attacks: print("Sem ataques disponiveis."); continue
            atk_labels = [f"{atk.name} ({atk.attack_type}) - {atk.cost}elec - val:{atk.value}" for atk in attacker.attacks]
            print(f"Ataques de {attacker.name}:")
            atk_pick = pick_index("Qual ataque?", atk_labels)
            attack = attacker.attacks[atk_pick]
            t_type = attack.attack_type.strip().lower()
            target_indices = []
            if t_type == "single":
                opp_alive = opp.alive_active()
                if not opp_alive: print("Oponente sem animatronics ativos."); continue
                t_idx = pick_index("Atacar qual animatronic do oponente?", opp_alive)
                target_indices = [opp.active.index(opp_alive[t_idx])]
            elif t_type == "stall":
                opp_alive = opp.alive_active()
                if not opp_alive: print("Oponente sem animatronics ativos."); continue
                t_idx = pick_index("Dar stall em qual animatronic?", opp_alive)
                target_indices = [opp.active.index(opp_alive[t_idx])]
            elif t_type == "heal":
                own_alive = p.alive_active()
                if own_alive and yes_no("Curar um animatronic especifico?"):
                    idx2 = pick_index("Curar qual?", own_alive)
                    target_indices = [p.active.index(own_alive[idx2])]
            if game.do_attack(a_idx, atk_pick, target_indices):
                attack_counts[a_idx] = attack_counts.get(a_idx,0) + 1

        elif choice == "4":
            supports = p.supports_in_hand()
            if not supports: print("Sem suportes na mao."); continue
            idx = pick_index("Usar qual suporte?", supports)
            game.do_use_support(supports[idx])

        elif choice == "5":
            all_anim = p.active + p.animatronics_in_hand()
            if not all_anim: print("Sem animatronics."); continue
            idx = pick_index("Ver detalhes de qual animatronic?", all_anim)
            a = all_anim[idx]
            print(f"\n{'─'*50}")
            print(f"  {a.name}")
            print(f"  HP: {a.current_hp}/{a.max_hp}  Elec: {a.electricity}/{a.max_electricity}")
            if a.ability_name:
                icon = "[ATIVA]" if a.ability_type=="active" else "[PASSIVA]"
                print(f"  {icon} {a.ability_name}")
                print(f"    {a.ability_desc}")
            for atk in a.attacks:
                print(f"  * {atk.name} [{atk.attack_type}] custo:{atk.cost}elec val:{atk.value}")
            print(f"{'─'*50}")

        elif choice == "6":
            actives = [(i,a) for i,a in enumerate(p.active)
                       if a.ability_type=="active" and a.ability_available()]
            if not actives:
                print("Nenhum animatronic com habilidade ativa disponivel.")
                for a in p.active:
                    if a.ability_type=="active":
                        if a.ability_used_this_turn: print(f"  {a.name}: ja usada este turno.")
                        elif a.ability_nullified_turns>0: print(f"  {a.name}: anulada ({a.ability_nullified_turns}t).")
                        elif a._ability_blocked_turns>0: print(f"  {a.name}: bloqueada ({a._ability_blocked_turns}t).")
                continue
            display_list = [f"{a.name} - {a.ability_name}: {a.ability_desc}" for _,a in actives]
            pick_n = pick_index("Usar habilidade de qual animatronic?", display_list)
            a_idx, _ = actives[pick_n]
            game.do_use_ability(a_idx)
        else:
            print("Opcao invalida.")

def run_ai_turn(game):
    import random
    p = game.current_player(); opp = game.opponent()
    print(f"\n[IA] Turno de {p.name}...")
    from engine.abilities import get_max_party
    for card in list(p.animatronics_in_hand()):
        if len(p.active) < get_max_party(p): p.place_animatronic(card)
    if not p.has_attached_electricity and p.electricity_in_hand() > 0:
        for a in p.active:
            if a.electricity < a.max_electricity: p.attach_electricity(a); break
    if not (game.round==1 and game.turn==game.first_player):
        for attacker in p.alive_active():
            if not attacker.can_attack(): continue
            from engine.abilities import extra_elec_cost
            for i,atk in enumerate(attacker.attacks):
                cost = atk.cost + extra_elec_cost(opp.active)
                if attacker.electricity >= cost:
                    t_type = atk.attack_type.strip().lower()
                    target_indices = []
                    if t_type in ("single","stall") and opp.alive_active():
                        t = random.choice(opp.alive_active())
                        target_indices = [opp.active.index(t)]
                    elif t_type=="heal" and p.alive_active():
                        target_indices = [p.active.index(p.alive_active()[0])]
                    game.do_attack(p.active.index(attacker), i, target_indices); break
    for a in p.alive_active():
        if a.ability_available() and random.random()<0.5:
            from engine.abilities import use_active_ability
            use_active_ability(a, game, game.turn); break
    for s in p.supports_in_hand():
        if random.random()<0.3: game.do_use_support(s); break
