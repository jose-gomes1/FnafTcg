"""FNAF TCG - Game Engine"""
import random
from engine.cards import AnimatronicCard, SupportCard, ElectricityCard
from engine.combat import resolve_attack
from engine.abilities import on_enter, on_death, start_of_turn_passives, end_of_turn_passives, get_max_party

POINTS_TO_WIN = 4

class Game:
    def __init__(self, p1, p2):
        self.players = [p1, p2]
        self.turn = 0; self.round = 1; self.first_player = 0
        self.game_over = False; self.winner = None
        self._log = []; self._extra_attack_ids = set()

    def log(self, msg): self._log.append(msg); print(msg)
    def flush_log(self):
        out = self._log[:]; self._log.clear(); return out

    def roll_for_first(self):
        rolls = [random.randint(1,6), random.randint(1,6)]
        while rolls[0]==rolls[1]: rolls=[random.randint(1,6),random.randint(1,6)]
        first = 0 if rolls[0]>rolls[1] else 1
        self.log(f"Dado: {self.players[0].name}={rolls[0]}, {self.players[1].name}={rolls[1]}")
        self.log(f"{self.players[first].name} escolhe se vai primeiro ou segundo!")
        self.first_player = first; return first

    def setup(self):
        mulligans = [0,0]
        for i,p in enumerate(self.players):
            m = p.setup_opening_hand(); mulligans[i] = m
            if m > 0: self.log(f"{p.name} teve {m} mulligan(s).")
        for i in range(2):
            opp = 1-i
            if mulligans[i]>0 and mulligans[opp]==0:
                self.players[opp].draw(1)
                self.log(f"{self.players[opp].name} tira 1 carta extra (Mulligan bonus).")

    def start_turn(self):
        p = self.current_player(); p.start_turn()
        if self.round>1 or self.turn!=self.first_player:
            if not p.deck:
                self.log(f"{p.name} nao tem mais cartas no deck! DERROTA POR DECKOUT!")
                self.game_over = True
                self.winner = self.players[1 - self.turn]
                return
            p.draw(1)
        self.log(f"\n{'='*50}\nTurno de {p.name} (Rodada {self.round})\n{'='*50}")
        self._extra_attack_ids = start_of_turn_passives(p, self, self.turn)

    def end_turn(self):
        p = self.current_player()
        end_of_turn_passives(p, self, self.turn)
        self._check_win_conditions()
        self.turn = 1-self.turn
        if self.turn==self.first_player: self.round += 1

    def current_player(self): return self.players[self.turn]
    def opponent(self): return self.players[1-self.turn]

    def _check_win_conditions(self):
        for i,p in enumerate(self.players):
            opp = self.players[1-i]

            # Process deaths: each dead animatronic = 1 point for attacker
            for card in [c for c in opp.active if not c.is_alive()]:
                revived = on_death(card, self, 1-i)
                if not revived:
                    if card in opp.active:
                        opp.active.remove(card)
                        opp.discard.append(card)
                    self.log(f"{card.name} foi derrotado!")
                    # Check Springbonnie: no point awarded on transform
                    if not getattr(card, 'springbonnie_transformed', False):
                        p.points += 1
                        self.log(f"{p.name} ganha 1 ponto por derrotar {card.name}! (Total: {p.points})")
                    if p.points >= POINTS_TO_WIN:
                        self.log(f"{p.name} chegou a {POINTS_TO_WIN} pontos! VITORIA!")
                        self.game_over=True; self.winner=p; return

            # If active is now empty, try to refill from hand only
            if len(opp.alive_active()) == 0 and len(opp.active) == 0:
                anim_in_hand = opp.animatronics_in_hand()
                if not anim_in_hand:
                    # No animatronics in hand -> immediate loss
                    self.log(f"{opp.name} nao tem mais animatronics em jogo! {p.name} VENCE!")
                    self.game_over=True; self.winner=p; return
                max_p = get_max_party(opp)
                for card in anim_in_hand:
                    if len(opp.active) < max_p:
                        opp.hand.remove(card)
                        opp.active.append(card)
                        on_enter(card, self, 1-i)

            if p.points >= POINTS_TO_WIN:
                self.log(f"{p.name} chegou a {POINTS_TO_WIN} pontos! VITORIA!")
                self.game_over=True; self.winner=p; return

    def do_attack(self, attacker_idx, attack_idx, target_indices):
        p = self.current_player(); opp = self.opponent()
        if attacker_idx>=len(p.active): self.log("Indice invalido."); return False
        attacker = p.active[attacker_idx]
        if attack_idx>=len(attacker.attacks): self.log("Indice invalido."); return False
        attack = attacker.attacks[attack_idx]
        t_type = attack.attack_type.strip().lower()
        if t_type in ("single","stall"): targets=[opp.active[i] for i in target_indices if i<len(opp.active)]
        elif t_type=="multi": targets=opp.alive_active()
        elif t_type=="heal": targets=[p.active[i] for i in target_indices if i<len(p.active)] if target_indices else []
        else: targets=[]
        if self.round==1 and self.turn==self.first_player:
            self.log("O primeiro jogador nao pode atacar no primeiro turno!"); return False
        elec_before = attacker.electricity
        for l in resolve_attack(attacker, attack, targets, p.active, opp.active, self): self.log(l)
        # electricity actually spent (gambling attacks may refund, so diff is correct)
        spent = elec_before - attacker.electricity
        for _ in range(max(0, spent)):
            p.discard.append(ElectricityCard())
        if attacker.name=="Endo-01" and attacker.passive_active():
            for t in targets:
                if t.is_alive(): attacker._endo01_rust_target = t
        self._check_win_conditions(); return True

    def do_place_animatronic(self, hand_idx):
        p = self.current_player()
        anim_hand = p.animatronics_in_hand()
        if hand_idx>=len(anim_hand): return False
        card = anim_hand[hand_idx]
        max_p = get_max_party(p)
        if len(p.active)>=max_p: self.log(f"Party cheia (maximo {max_p})."); return False
        if p.place_animatronic(card):
            self.log(f"{p.name} coloca {card.name} na party!")
            on_enter(card, self, self.turn); return True
        return False

    def do_attach_electricity(self, active_idx):
        p = self.current_player()
        if active_idx>=len(p.active): return False
        if p.attach_electricity(p.active[active_idx]):
            self.log(f"Eletricidade attachada a {p.active[active_idx].name}!"); return True
        self.log("Nao podes attchar eletricidade agora."); return False

    def do_use_support(self, support):
        p = self.current_player()
        if any(a._supports_blocked_turns>0 for a in p.active):
            self.log("Nao podes usar supporters este turno!"); return False
        return p.use_support(support, self, self.turn)

    def do_use_ability(self, active_idx):
        from engine.abilities import use_active_ability
        p = self.current_player()
        if active_idx>=len(p.active): return False
        return use_active_ability(p.active[active_idx], self, self.turn)

    def card_has_extra_attack(self, card):
        return id(card) in self._extra_attack_ids