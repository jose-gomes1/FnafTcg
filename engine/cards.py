"""FNAF TCG - Card Data Models"""
import csv, os
from typing import Optional

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

class Attack:
    def __init__(self, name, attack_type, cost, value):
        self.name = name
        self.attack_type = attack_type
        self.cost = cost
        self.value = value
    def __str__(self):
        return f"{self.name} ({self.attack_type}) {self.cost}elec val:{self.value}"

class AnimatronicCard:
    def __init__(self, name, max_hp, max_electricity, attacks,
                 ability_name="", ability_type="", ability_desc=""):
        self.name = name
        self.max_hp = max_hp
        self.max_electricity = max_electricity
        self.attacks = attacks
        self.ability_name = ability_name
        self.ability_type = ability_type   # "active" | "passive" | ""
        self.ability_desc = ability_desc
        # runtime state
        self.current_hp = max_hp
        self.electricity = 0
        self.stalled_turns = 0
        self.ability_used_this_turn = False
        self.ability_nullified_turns = 0
        self._ability_blocked_turns = 0
        self.has_survived_once = False
        self.springbonnie_transformed = False
        self.phantom_chica_locked = None
        self._freddy_mask = False
        self._damage_reduction = 0
        self._sonic_echo_turns = 0
        self._double_damage_turn = False
        self._rainy_day_bonus = 0
        self._no_heal_turns = 0
        self._redirecting = False
        self._extra_elec_cost = 0
        self._supports_blocked_turns = 0
        self._puppet_protected = False
        self._last_attacker = None
        self._endo01_rust_target = None
        self._reroll_used = False

    def is_alive(self):
        return self.current_hp > 0

    def can_attack(self):
        return self.stalled_turns <= 0

    def ability_available(self):
        return (self.ability_type == "active"
                and not self.ability_used_this_turn
                and self.ability_nullified_turns <= 0
                and self._ability_blocked_turns <= 0)

    def passive_active(self):
        return (self.ability_type == "passive"
                and self.ability_nullified_turns <= 0
                and self._ability_blocked_turns <= 0)

    def take_damage(self, dmg, source=None):
        if dmg <= 0:
            return 0
        actual = max(0, dmg - self._damage_reduction) + self._rainy_day_bonus
        if self._puppet_protected and actual >= self.current_hp:
            self.current_hp = 10
            self._puppet_protected = False
            if source: self._last_attacker = source
            return actual
        if self.name == "Glamrock Endo" and not self.has_survived_once and actual >= self.current_hp:
            self.current_hp = 10
            self.has_survived_once = True
            if source: self._last_attacker = source
            return actual
        self.current_hp = max(0, self.current_hp - actual)
        if source: self._last_attacker = source
        return actual

    def heal(self, amount):
        if self._no_heal_turns > 0:
            return
        self.current_hp = min(self.max_hp, self.current_hp + amount)

    def attach_electricity(self):
        if self.electricity < self.max_electricity:
            self.electricity += 1
            return True
        return False

    def spend_electricity(self, amount):
        if self.electricity >= amount:
            self.electricity -= amount
            return True
        return False

    def tick_turn(self):
        if self.stalled_turns > 0: self.stalled_turns -= 1
        self.ability_used_this_turn = False
        self._reroll_used = False
        if self.ability_nullified_turns > 0: self.ability_nullified_turns -= 1
        if self._ability_blocked_turns > 0: self._ability_blocked_turns -= 1
        if self._no_heal_turns > 0: self._no_heal_turns -= 1
        if self._supports_blocked_turns > 0: self._supports_blocked_turns -= 1
        if self._sonic_echo_turns > 0:
            self._sonic_echo_turns -= 1
            if self._sonic_echo_turns == 0:
                self._damage_reduction = 0
        self._rainy_day_bonus = 0
        self._double_damage_turn = False
        self._endo01_rust_target = None

    def clone(self):
        return AnimatronicCard(self.name, self.max_hp, self.max_electricity,
                               self.attacks, self.ability_name,
                               self.ability_type, self.ability_desc)

    def __str__(self):
        stall = f" [STALL {self.stalled_turns}t]" if self.stalled_turns > 0 else ""
        null = " [NULL]" if self.ability_nullified_turns > 0 else ""
        return f"{self.name} | HP:{self.current_hp}/{self.max_hp} | elec:{self.electricity}/{self.max_electricity}{stall}{null}"

class SupportCard:
    def __init__(self, name, description):
        self.name = name
        self.description = description
    def __str__(self):
        return f"[Suporte] {self.name}: {self.description}"

class ElectricityCard:
    name = "Eletricidade"
    def __str__(self): return "Eletricidade"

ABILITY_DATA = {
    "Freddy": ("Busca de Energia","active","Procura 1 eletricidade no deck e liga-a a Freddy."),
    "Bonnie": ("Imunidade a Stall","passive","Bonnie nao pode receber Stall de ataques."),
    "Chica": ("Cura das Chicas","active","Cura 10 HP de um animatronic 'Chica' na party."),
    "Foxy": ("Mordida Rapida","active","Coloca 5 dano num animatronic do oponente."),
    "Golden Freddy": ("Jumpscare Passivo","active","Coloca um animatronic do oponente em stall por 1 turno."),
    "Toy Freddy": ("Imunidade a Stall","passive","Toy Freddy e imune a ataques Stall."),
    "Toy Bonnie": ("Corte de Energia","active","Descarta 1 eletricidade de um animatronic do oponente."),
    "Toy Chica": ("Provocacao","active","Redireciona todos os ataques do oponente para Toy Chica por 1 turno."),
    "Toy Foxy (Mangle)": ("Corpo Duplo","passive","Imune ao suporte Flashlight. Toma 2x dano de animatronics Foxy."),
    "Withered Freddy": ("Busca de Energia","active","Procura 1 eletricidade no deck e liga-a a Withered Freddy."),
    "Withered Bonnie": ("Armadura Withered","passive","Animatronics Withered teus tomam -30 de dano (stacka 1x)."),
    "Withered Chica": ("Cura Amplificada","passive","Animatronics Withered teus recebem 2x cura (nao stacka)."),
    "Withered Foxy": ("Sem Mascara","passive","Withered Foxy nao e afetado pelo suporte Freddy Mask."),
    "Withered Golden Freddy": ("Party Expandida","passive","Com mais Withered em jogo, maximo da party sobe para 6."),
    "Puppet": ("Sobrevivencia Forcada","active","Escolhe um animatronic. Sobrevive ao proximo ataque fatal com 10 HP."),
    "Balloon Boy": ("Baloes Toxicos","active","Coloca 10 dano em todos os animatronics do oponente."),
    "JJ": ("Transferencia de Dano","active","Move 40 dano da tua party para a party do oponente."),
    "Springbonnie": ("Transformacao","passive","Ao morrer, nao da ponto. Substitui-se por um animatronic com 'trap' no nome."),
    "RWQFSFASXC": ("Anulacao Glitch","active","Descarta 1 eletricidade da mao para anular a habilidade de um animatronic do oponente por 2 turnos."),
    "Shadow Freddy": ("Relancamento de Dado","passive","Ao falhar um dado, pode relanca-lo uma vez por turno."),
    "Phantom Freddy": ("Transferencia Fantasma","active","Move 40 dano da tua party para a party do oponente."),
    "Phantom Foxy": ("Entrada Assustadora","passive","Ao entrar em campo, coloca 20 dano num animatronic do oponente."),
    "Phantom Chica": ("Bloqueio de Ataque","active","Escolhe um animatronic do oponente. Enquanto em jogo, so pode usar Single Target."),
    "Phantom Mangle": ("Interferencia","passive","Ataques do oponente requerem 1 eletricidade extra enquanto em jogo."),
    "Phantom Balloon Boy": ("Dado Toxico","active","Dado: par=descarta 1 elec do oponente; impar=descarta 1 elec de cada animatronic teu."),
    "Phantom Puppet": ("Maldicao de Morte","passive","Ao morrer, coloca 2 animatronics do oponente em stall por 2 turnos."),
    "Springtrap": ("Forca Phantom","passive","Para cada animatronic Phantom na tua party, Springtrap causa +10 dano."),
    "Nightmare Freddy": ("Suprimir Habilidades","passive","Desativa habilidades de animatronics sem Nightmare enquanto em campo."),
    "Nightmare Bonnie": ("Reciclagem de Energia","passive","Liga eletricidades descartadas a animatronics Nightmare; ao usa-las voltam ao deck."),
    "Nightmare Chica": ("Entrada Paralisante","passive","Ao entrar na party, stall em 2 animatronics do oponente por 1 turno."),
    "Nightmare Foxy": ("Escudo Nightmare","passive","Animatronics Nightmare teus tomam metade do dano (nao stacka)."),
    "Nightmare Fredbear": ("Imune a Stall de Habilidades","passive","Nightmare Fredbear nao pode receber stall de habilidades."),
    "Nightmare": ("Imune a Stall de Habilidades","passive","Nightmare nao pode receber stall de habilidades."),
    "Plushtrap": ("Amplificacao Nightmare","passive","No turno de entrada, animatronics Nightmare (ambos lados) dao 2x dano."),
    "Jack-O-Bonnie": ("Chama Descartada","active","Liga 1 eletricidade do descarte a Jack-O-Bonnie."),
    "Jack-O-Chica": ("Chama Descartada","active","Liga 1 eletricidade do descarte a Jack-O-Chica."),
    "Nightmare Mangle": ("Chama Descartada","active","Liga 1 eletricidade do descarte a Nightmare Mangle."),
    "Nightmare Balloon Boy": ("Chama Descartada","active","Liga 1 eletricidade do descarte a Nightmare Balloon Boy."),
    "Nightmarionne": ("Toque da Morte","active","Coloca 20 dano num animatronic do oponente."),
    "Endo-01": ("Ferrugem","passive","No fim do turno, se causou dano, o alvo perde 10 HP extra."),
    "Endo-02": ("Reviver","passive","Na primeira morte, dado: se par revive com 50 HP sem dar ponto."),
    "Springlock Endo": ("Mecanismo de Mola","passive","Inicio do turno, dado: par=animatronics Fnaf3 teus atacam 1x a mais."),
    "Nightmare Endo": ("Bloqueio de Cura","passive","Alvos de Nightmare Endo nao regeneram HP no proximo turno."),
    "Plush Endo": ("Reflexo de Dano","passive","Ao morrer, reflete o dano do ultimo ataque sofrido no atacante."),
    "Funtime Endo": ("Relancamento de Dado","passive","Ao falhar um dado, pode relanca-lo uma vez por turno."),
    "Glamrock Endo": ("Armadura Glamrock","passive","Sobrevive a um ataque fatal com 10 HP (uma unica vez)."),
    "The Mimic (M2)": ("Copia de Habilidade","active","Copia a habilidade de qualquer animatronic em jogo e usa-a."),
}

FNAF3_NAMES = frozenset({
    "Springbonnie","RWQFSFASXC","Shadow Freddy","Phantom Freddy","Phantom Foxy",
    "Phantom Chica","Phantom Mangle","Phantom Balloon Boy","Phantom Puppet","Springtrap",
})

def load_animatronics():
    path = os.path.join(DATA_DIR, "animatronics.csv")
    result = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            attacks = []
            for i in (1, 2):
                n = row.get(f"Attack{i}Name","").strip()
                if n:
                    attacks.append(Attack(n, row[f"Attack{i}Type"].strip(),
                        int(row[f"Attack{i}Cost"]),
                        int(row[f"Attack{i}Value"]) if row[f"Attack{i}Value"] else 0))
            name = row["Name"].strip()
            ab = ABILITY_DATA.get(name, ("","",""))
            result[name] = AnimatronicCard(name, int(row["HP"]),
                int(row["MaxElectricity"]), attacks, ab[0], ab[1], ab[2])
    return result

def load_supports():
    path = os.path.join(DATA_DIR, "supports.csv")
    result = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            result[row["Name"].strip()] = SupportCard(row["Name"].strip(), row["Description"].strip())
    return result

ANIMATRONICS = load_animatronics()
SUPPORTS = load_supports()
