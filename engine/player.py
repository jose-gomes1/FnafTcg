"""
FNAF TCG - Player State
"""
import random
from engine.cards import AnimatronicCard, SupportCard, ElectricityCard

HAND_SIZE = 3
MAX_ACTIVE = 4
MULLIGAN_LIMIT = 3


class Player:
    def __init__(self, name: str, deck: list):
        self.name = name
        self.deck: list = deck[:]
        self.hand: list = []
        self.active: list[AnimatronicCard] = []  # up to 4
        self.discard: list = []
        self.points: int = 0
        self.has_attached_electricity: bool = False  # per turn limit

    # ── Draw / Mulligan ──────────────────────────────────────────────────────

    def draw(self, n: int = 1) -> list:
        drawn = []
        for _ in range(n):
            if self.deck:
                drawn.append(self.deck.pop(0))
        self.hand.extend(drawn)
        return drawn

    def shuffle_deck(self):
        random.shuffle(self.deck)

    def has_animatronic_in_hand(self) -> bool:
        return any(isinstance(c, AnimatronicCard) for c in self.hand)

    def setup_opening_hand(self) -> int:
        """Draw opening hand, perform mulligans. Returns number of mulligans taken."""
        mulligans = 0
        self.draw(HAND_SIZE)

        while not self.has_animatronic_in_hand():
            if mulligans >= MULLIGAN_LIMIT:
                # Force-find an animatronic
                self._force_find_animatronic()
                return mulligans
            # Return hand to deck, reshuffle, redraw
            self.deck.extend(self.hand)
            self.hand.clear()
            self.shuffle_deck()
            self.draw(HAND_SIZE)
            mulligans += 1

        return mulligans

    def _force_find_animatronic(self):
        """Find first animatronic in deck, put in hand, reshuffle rest, draw 2 more."""
        pre_search = []
        found = None
        for card in self.deck:
            if found is None and isinstance(card, AnimatronicCard):
                found = card
            else:
                pre_search.append(card)
        self.deck = pre_search
        self.shuffle_deck()
        if found:
            self.hand.append(found)
        self.draw(2)

    # ── Active Party Management ──────────────────────────────────────────────

    def place_animatronic(self, card: AnimatronicCard) -> bool:
        if len(self.active) >= MAX_ACTIVE:
            return False
        if card in self.hand:
            self.hand.remove(card)
            self.active.append(card)
            return True
        return False

    def remove_dead(self):
        dead = [c for c in self.active if not c.is_alive()]
        for c in dead:
            self.active.remove(c)
            self.discard.append(c)
        return dead

    # ── Electricity ──────────────────────────────────────────────────────────

    def attach_electricity(self, target: AnimatronicCard) -> bool:
        """Attach 1 electricity from hand to an active animatronic. Once per turn."""
        if self.has_attached_electricity:
            return False
        elec = next((c for c in self.hand if isinstance(c, ElectricityCard)), None)
        if elec is None:
            return False
        if target not in self.active:
            return False
        if not target.attach_electricity():
            return False
        self.hand.remove(elec)
        self.discard.append(elec)
        self.has_attached_electricity = True
        return True

    # ── Support Cards ─────────────────────────────────────────────────────────

    def use_support(self, card: SupportCard, game, player_idx: int):
        """Execute support card effect and discard it."""
        if card not in self.hand:
            return False
        result = apply_support(card, game, player_idx)
        if result:
            self.hand.remove(card)
            self.discard.append(card)
        return result

    # ── Turn Reset ───────────────────────────────────────────────────────────

    def start_turn(self):
        self.has_attached_electricity = False
        for a in self.active:
            a.tick_turn()

    # ── Helpers ──────────────────────────────────────────────────────────────

    def alive_active(self) -> list[AnimatronicCard]:
        return [a for a in self.active if a.is_alive()]

    def animatronics_in_hand(self) -> list[AnimatronicCard]:
        return [c for c in self.hand if isinstance(c, AnimatronicCard)]

    def electricity_in_hand(self) -> int:
        return sum(1 for c in self.hand if isinstance(c, ElectricityCard))

    def supports_in_hand(self) -> list[SupportCard]:
        return [c for c in self.hand if isinstance(c, SupportCard)]

    def __str__(self):
        return (
            f"=== {self.name} | Pontos: {self.points} ===\n"
            f"  Mão: {len(self.hand)} cartas "
            f"({len(self.animatronics_in_hand())} anim, "
            f"{self.electricity_in_hand()} elec, "
            f"{len(self.supports_in_hand())} suporte)\n"
            f"  Deck: {len(self.deck)} | Descarte: {len(self.discard)}\n"
            f"  Ativos:\n"
            + "\n".join(f"    [{i}] {a}" for i, a in enumerate(self.active))
        )


# ── Support Effects ───────────────────────────────────────────────────────────

def apply_support(card: SupportCard, game, player_idx: int) -> bool:
    """
    Apply support card effect. Returns True if successfully used.
    game is the Game instance; player_idx is 0 or 1.
    Interactive prompts are handled here.
    """
    from ui.cli import pick_index, yes_no, pick_animatronic_from_deck

    player = game.players[player_idx]
    opponent = game.players[1 - player_idx]
    name = card.name

    if name == "Cupcake":
        for a in player.active:
            a.heal(20)
        game.log(f"{player.name} usa Cupcake — cura 20 HP de toda a party!")
        return True

    elif name == "Mini Cupcake":
        if not player.active:
            game.log("Nenhum animatronic ativo para curar.")
            return False
        idx = pick_index("Curar qual animatronic?", player.active)
        player.active[idx].heal(10)
        game.log(f"{player.name} usa Mini Cupcake — cura 10 HP de {player.active[idx].name}!")
        return True

    elif name == "Henry Emily":
        result = pick_animatronic_from_deck(player)
        if result:
            game.log(f"{player.name} usa Henry Emily — coloca {result.name} na party!")
        return result is not None

    elif name == "William Afton":
        import random
        roll = random.randint(1, 6)
        game.log(f"{player.name} usa William Afton — dado: {roll}!")
        if roll % 2 == 0:
            # Even: deal 60 damage to opponent's party, distributed freely
            total = 60
            game.log(f"Par! Distribui 60 de dano pelos animatronics do oponente.")
            targets = opponent.alive_active()
            if not targets:
                game.log("Oponente não tem animatronics ativos.")
                return True
            remaining = total
            for t in targets:
                if remaining <= 0:
                    break
                dmg = min(remaining, t.current_hp)
                t.take_damage(dmg)
                remaining -= dmg
                game.log(f"  {t.name} recebe {dmg} dano.")
        else:
            game.log(f"Ímpar! Toda a sua party recebe 15 de dano.")
            for a in player.active:
                a.take_damage(15)
        return True

    elif name == "Power Out":
        targets = opponent.alive_active()
        if not targets:
            return False
        idx = pick_index("Remover eletricidade de qual animatronic do oponente?", targets)
        t = targets[idx]
        if t.electricity > 0:
            t.electricity -= 1
            game.log(f"{player.name} usa Power Out — remove 1 eletricidade de {t.name}!")
        else:
            game.log(f"{t.name} não tem eletricidade.")
        return True

    elif name == "Flashlight":
        foxy_targets = [a for a in opponent.alive_active() if "Foxy" in a.name]
        if not foxy_targets:
            game.log("Nenhum Foxy do oponente para dar stall.")
            return False
        for t in foxy_targets:
            t.stalled_turns += 2
        names = ", ".join(t.name for t in foxy_targets)
        game.log(f"{player.name} usa Flashlight — {names} ficam em stall por 2 turnos!")
        return True

    elif name == "Freddy Mask":
        if not player.active:
            return False
        idx = pick_index("Proteger qual animatronic com a Freddy Mask?", player.active)
        target = player.active[idx]
        target._freddy_mask = True
        game.log(f"{player.name} usa Freddy Mask em {target.name}!")
        # Nullify Withered Bonnie ability on opponent side
        wb = next((a for a in opponent.alive_active() if a.name == "Withered Bonnie"), None)
        if wb:
            wb._ability_nullified = True
            game.log("Habilidade de Withered Bonnie anulada por 1 turno!")
        return True

    elif name == "Mendo's Endos":
        if not player.active:
            return False
        idx = pick_index("Aumentar HP de qual animatronic?", player.active)
        player.active[idx].max_hp += 20
        player.active[idx].current_hp += 20
        game.log(f"{player.name} usa Mendo's Endos — {player.active[idx].name} ganha 20 HP!")
        return True

    elif name == "DD's Pearl":
        anim_elec = [c for c in player.discard
                     if isinstance(c, AnimatronicCard) or isinstance(c, ElectricityCard)]
        to_return = anim_elec[:5]
        for c in to_return:
            player.discard.remove(c)
            player.deck.append(c)
        player.shuffle_deck()
        game.log(f"{player.name} usa DD's Pearl — {len(to_return)} cartas voltam ao deck!")
        return True

    elif name == "Power Drain":
        # Discard 2 electricity from hand, search for an animatronic
        elec_in_hand = [c for c in player.hand if isinstance(c, ElectricityCard)]
        if len(elec_in_hand) < 2:
            game.log("Não tens 2 eletricidades na mão para usar Power Drain.")
            return False
        for c in elec_in_hand[:2]:
            player.hand.remove(c)
            player.discard.append(c)
        result = pick_animatronic_from_deck(player)
        if result:
            game.log(f"{player.name} usa Power Drain — descarta 2 ⚡, busca {result.name}!")
        return True

    elif name == "Edwin":
        from engine.cards import ANIMATRONICS
        mimic = next((c for c in player.deck if isinstance(c, AnimatronicCard)
                      and c.name == "The Mimic (M2)"), None)
        if mimic:
            player.deck.remove(mimic)
            player.hand.append(mimic)
            player.shuffle_deck()
            game.log(f"{player.name} canta a parte do Edwin... e encontra The Mimic (M2)!")
        else:
            game.log("The Mimic (M2) não está no deck.")
        return True

    game.log(f"Suporte '{name}' ainda não implementado.")
    return False
