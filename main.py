"""
FNAF TCG - Main Entry Point
Run: python main.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import random
from engine.deck import get_default_deck
from engine.player import Player
from engine.game import Game
from ui.cli import run_player_turn, run_ai_turn, yes_no, pick_index

BANNER = "\033[91m" + r"""
███████╗   ███╗   ██╗        █████╗     ███████╗          ████████╗      ██████╗     ██████╗ 
██╔════╝   ████╗  ██║       ██╔══██╗    ██╔════╝          ╚══██╔══╝     ██╔════╝    ██╔════╝ 
█████╗     ██╔██╗ ██║       ███████║    █████╗               ██║        ██║         ██║  ███╗
██╔══╝     ██║╚██╗██║       ██╔══██║    ██╔══╝               ██║        ██║         ██║   ██║
██║        ██║ ╚████║       ██║  ██║    ██║                  ██║        ╚██████╗    ╚██████╔╝
╚═╝ive     ╚═╝  ╚═══╝ights  ╚═╝  ╚═╝t   ╚═╝reddys            ╚═╝rading   ╚═════╝ard  ╚═════╝ ame
hur hur hur hur huuuur 
""" + "\033[0m"


def main():
    print(BANNER)

    mode = pick_index(
        "Modo de jogo:",
        ["Jogador vs IA", "Jogador vs Jogador (pass-and-play)"],
    )

    p1_name = input("Nome do Jogador 1: ").strip() or "Jogador 1"
    if mode == 1:
        p2_name = input("Nome do Jogador 2: ").strip() or "Jogador 2"
    else:
        p2_name = "IA"

    print("\nA criar decks...")
    p1 = Player(p1_name, get_default_deck())
    p2 = Player(p2_name, get_default_deck())

    game = Game(p1, p2)

    # Decide first player
    print("\nA rolar o dado para decidir quem vai primeiro...")
    first = game.roll_for_first()
    winner_roll = game.players[first]
    choice = pick_index(
        f"{winner_roll.name} ganhou o dado. Quer ir:",
        ["Primeiro", "Segundo"],
    )
    if choice == 1:
        game.first_player = 1 - first
    game.turn = game.first_player
    print(f"\n{game.players[game.first_player].name} vai primeiro!\n")

    # Setup opening hands
    game.setup()

    # Each player places opening animatronics (hidden)
    for i, p in enumerate(game.players):
        if mode == 1 and i == 1:
            # AI auto-place
            for card in p.animatronics_in_hand():
                if len(p.active) < 4:
                    p.active.append(card)
                    p.hand.remove(card)
        else:
            if mode == 1 or i == 0:
                print(f"\n{p.name} — coloca o(s) teu(s) animatronic(s) inicial(is).")
            else:
                input(f"\nPassa o ecrã para {p.name} e carrega ENTER...")

            placed = False
            while not placed:
                anim_hand = p.animatronics_in_hand()
                if not anim_hand:
                    print("Nenhum animatronic na mão!")
                    break
                print("Animatronics na mão:")
                for idx, c in enumerate(anim_hand):
                    print(f"  [{idx}] {c.name}  HP:{c.max_hp}  MaxElec:{c.max_electricity}")
                raw = input("Índices a colocar (separados por espaço): ").strip()
                try:
                    idxs = [int(x) for x in raw.split()]
                    for idx in idxs:
                        if 0 <= idx < len(anim_hand):
                            p.place_animatronic(anim_hand[idx])
                    placed = True
                except ValueError:
                    print("Entrada inválida.")

    print("\nJogo começa!")

    # ── Main Game Loop ────────────────────────────────────────────────────────
    while not game.game_over:
        game.start_turn()
        current = game.current_player()
        is_ai = mode == 0 and current == p2

        if not current.active:
            # Try to place from hand
            for card in current.animatronics_in_hand():
                if len(current.active) < 4:
                    current.active.append(card)
                    current.hand.remove(card)
            if not current.active:
                game.log(f"{current.name} não tem animatronics! Perde um ponto.")
                game.players[1 - game.turn].points += 1
                game.end_turn()
                continue

        if is_ai:
            run_ai_turn(game)
        else:
            if mode == 1:
                input(f"\nPassa o ecrã para {current.name} e carrega ENTER...")
            run_player_turn(game)

        game.end_turn()

    # ── Game Over ─────────────────────────────────────────────────────────────
    print("\n" + "★" * 50)
    if game.winner:
        print(f"  🎉 {game.winner.name} GANHOU O JOGO! 🎉")
    else:
        print("  Empate!")
    print("★" * 50)
    print(f"\nPontuação final:")
    for p in game.players:
        print(f"  {p.name}: {p.points} pontos")


if __name__ == "__main__":
    main()
