#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
using namespace std;

enum class CardType { Animatronic, Support, Electricity };

struct Attack {
    string name;
    string target; // Single, Multi, etc
    int cost;
    int value;
};

struct Card {
    string name;
    CardType type;
    int hp = 0;
    int currentHP = 0;
    int maxElectricity = 0;
    int attachedElectricity = 0;
    Attack atk1;
    Attack atk2;
    string ability; // habilidade especial
};

vector<Card> deck;
vector<Card> hand;
vector<Card> active;
vector<Card> discardPile;

bool attachedThisTurn = false;
int mulligans = 0;

random_device rd;
mt19937 rng(rd());

// ========================= Deck / Cards =========================

Card createAnim(string name, int hp, int maxE, Attack atk1 = Attack(), Attack atk2 = Attack(), string ability = "") {
    Card c;
    c.name = name;
    c.type = CardType::Animatronic;
    c.hp = hp;
    c.currentHP = hp;
    c.maxElectricity = maxE;
    c.atk1 = atk1;
    c.atk2 = atk2;
    c.ability = ability;
    return c;
}

Card createSupport(string name, string desc = "") {
    Card c;
    c.name = name;
    c.type = CardType::Support;
    c.ability = desc;
    return c;
}

Card createEnergy() {
    Card c;
    c.name = "Eletricidade";
    c.type = CardType::Electricity;
    return c;
}

// ========================= Funções base =========================

void shuffleDeck() {
    shuffle(deck.begin(), deck.end(), rng);
}

void drawCard() {
    if(deck.empty()) {
        cout << "Deck vazio!\n";
        return;
    }
    Card c = deck.back();
    deck.pop_back();
    hand.push_back(c);
    cout << "Você comprou: " << c.name << endl;
}

bool hasAnimatronic() {
    for(auto &c : hand)
        if(c.type == CardType::Animatronic)
            return true;
    return false;
}

void setupInitialHand() {
    while(true) {
        hand.clear();
        for(int i=0;i<3;i++) drawCard();
        if(hasAnimatronic()) break;

        mulligans++;
        cout << "Mulligan #" << mulligans << endl;

        deck.insert(deck.end(), hand.begin(), hand.end());
        shuffleDeck();

        if(mulligans == 3) {
            cout << "3 Mulligans! Garantindo animatronic na mão...\n";
            auto it = find_if(deck.begin(), deck.end(), [](Card &c){ return c.type == CardType::Animatronic; });
            if(it != deck.end()) {
                hand.push_back(*it);
                deck.erase(it);
                shuffleDeck();
            } else {
                cout << "Nenhum animatronic restante no deck!\n";
            }
            drawCard();
            drawCard();
            break;
        }
    }
    cout << "Total de Mulligans: " << mulligans << endl;
}

// ========================= Mostrar =========================

void showHand() {
    cout << "\n=== MÃO ===\n";
    for(int i=0;i<hand.size();i++)
        cout << i << " - " << hand[i].name << endl;
}

void showActive() {
    cout << "\n=== ATIVOS ===\n";
    for(int i=0;i<active.size();i++) {
        Card &c = active[i];
        cout << i << " - " << c.name
             << " HP: " << c.currentHP << "/" << c.hp
             << " Energia: " << c.attachedElectricity << "/" << c.maxElectricity << endl;
        if(c.atk1.name != "") cout << "   Ataque1: " << c.atk1.name << " (" << c.atk1.target << ", Custo " << c.atk1.cost << ", Dano " << c.atk1.value << ")\n";
        if(c.atk2.name != "") cout << "   Ataque2: " << c.atk2.name << " (" << c.atk2.target << ", Custo " << c.atk2.cost << ", Dano " << c.atk2.value << ")\n";
        if(c.ability != "") cout << "   Habilidade: " << c.ability << "\n";
    }
}

void showDeckContents() {
    cout << "\n=== DECK ===\n";
    vector<string> names;
    vector<int> counts;
    for(auto &c : deck) {
        auto it = find(names.begin(), names.end(), c.name);
        if(it != names.end()) {
            int idx = distance(names.begin(), it);
            counts[idx]++;
        } else {
            names.push_back(c.name);
            counts.push_back(1);
        }
    }
    for(int i=0;i<names.size();i++)
        cout << names[i] << " x" << counts[i] << endl;
}

// ========================= Jogabilidade =========================

void placeActive() {
    if(active.size() >= 4) {
        cout << "Limite de 4 ativos!\n";
        return;
    }
    showHand();
    int choice;
    cout << "Escolha carta para colocar como ativo: ";
    cin >> choice;

    if(choice >=0 && choice < hand.size() && hand[choice].type == CardType::Animatronic) {
        active.push_back(hand[choice]);
        hand.erase(hand.begin()+choice);
        cout << "Animatronic colocado!\n";
    } else {
        cout << "Escolha inválida!\n";
    }
}

void useCard() {
    showHand();
    int choice;
    cout << "Escolha carta para usar: ";
    cin >> choice;
    if(choice <0 || choice >= hand.size()) return;

    Card &c = hand[choice];
    if(c.type == CardType::Electricity) {
        if(attachedThisTurn) {
            cout << "Ja ligou eletricidade este turno!\n";
            return;
        }
        showActive();
        int target;
        cout << "Escolha ativo para ligar eletricidade: ";
        cin >> target;
        if(target >=0 && target < active.size() && active[target].attachedElectricity < active[target].maxElectricity) {
            active[target].attachedElectricity++;
            hand.erase(hand.begin()+choice);
            attachedThisTurn = true;
            cout << "Energia ligada!\n";
        }
    } else if(c.type == CardType::Support) {
        cout << "Support usado: " << c.name << endl;
        discardPile.push_back(c);
        hand.erase(hand.begin()+choice);
    }
}

void editHP() {
    showActive();
    int i;
    cout << "Escolha animatronic para editar HP: ";
    cin >> i;
    if(i >=0 && i < active.size()) {
        int newHP;
        cout << "Novo HP: ";
        cin >> newHP;
        active[i].currentHP = newHP;
        if(active[i].currentHP <=0) {
            cout << "Animatronic morreu!\n";
            discardPile.push_back(active[i]);
            active.erase(active.begin()+i);
        }
    }
}

void useActiveAbility() {
    showActive();
    int i;
    cout << "Escolha animatronic ativo para usar habilidade: ";
    cin >> i;

    if(i >=0 && i < active.size()) {
        Card &c = active[i];
        cout << c.name << " usou sua habilidade: " << c.ability << "\n";

        // Exemplo de habilidade que liga energia automaticamente
        if(c.ability.find("Procura eletricidade") != string::npos) {
            if(c.attachedElectricity < c.maxElectricity) {
                // procura uma carta de eletricidade na mão
                auto it = find_if(hand.begin(), hand.end(), [](Card &x){ return x.type == CardType::Electricity; });
                if(it != hand.end()) {
                    c.attachedElectricity++;
                    cout << "Eletricidade ligada automaticamente a " << c.name << "!\n";
                    hand.erase(it); // remove da mão
                    attachedThisTurn = true;
                } else {
                    cout << "Nenhuma eletricidade disponível na mão para ligar.\n";
                }
            } else {
                cout << c.name << " já está com eletricidade máxima!\n";
            }
        }

        // Outras habilidades podem ser adicionadas aqui
    }
}

void discardCard() {
    cout << "Deseja descartar da mão (0) ou dos ativos (1)? ";
    int choice; cin >> choice;

    if(choice == 0) {
        showHand();
        int i; cout << "Escolha carta da mão para descartar: "; cin >> i;
        if(i>=0 && i<hand.size()) {
            discardPile.push_back(hand[i]);
            cout << "Descartou: " << hand[i].name << endl;
            hand.erase(hand.begin()+i);
        }
    } else if(choice == 1) {
        showActive();
        int i; cout << "Escolha animatronic ativo para descartar: "; cin >> i;
        if(i>=0 && i<active.size()) {
            discardPile.push_back(active[i]);
            cout << "Descartou animatronic ativo: " << active[i].name << endl;
            active.erase(active.begin()+i);
        }
    }
}

// ========================= Main =========================

int main() {

    // ====== Exemplo simples de animatronics ======
    vector<Card> anims;
    anims.push_back(createAnim("Withered Freddy",125,3,{"Mic Toss","Single",1,20},{"Unscrew","Single",2,120},"Procura eletricidade e liga"));
    anims.push_back(createAnim("Shadow Freddy",150,3,{"ESC Key","Single",1,25},{"", "",0,0},"Refaz ataque se falhar dado"));
    anims.push_back(createAnim("Jack-O-Bonnie",200,5,{"Flame Strike","Single",2,40},{"", "",0,0},""));
    anims.push_back(createAnim("Jack-O-Chica",200,5,{"Inferno Feast","Single",2,50},{"", "",0,0},""));

    // ====== Exemplo simples de suportes ======
    vector<Card> supports;
    supports.push_back(createSupport("Freddy Mask","Protege animatronics de Toy/Withered"));
    supports.push_back(createSupport("William Afton","Dano ao oponente baseado em dado"));
    supports.push_back(createSupport("Power Drain","Descarta eletricidades para buscar animatronic"));

    // ====== Funções para buscar carta pelo nome ======
    auto findAnim = [&](string name) -> Card {
        auto it = find_if(anims.begin(), anims.end(), [&](Card &c){ return c.name==name; });
        if(it!=anims.end()) return *it;
        else { cout << "Animatronic não encontrado: " << name << endl; return Card(); }
    };
    auto findSupport = [&](string name) -> Card {
        auto it = find_if(supports.begin(), supports.end(), [&](Card &c){ return c.name==name; });
        if(it!=supports.end()) return *it;
        else { cout << "Suporte não encontrado: " << name << endl; return Card(); }
    };

    // ====== Montando deck ======
    deck.clear();
    for(int i=0;i<3;i++) deck.push_back(findAnim("Withered Freddy"));
    for(int i=0;i<2;i++) deck.push_back(findAnim("Shadow Freddy"));
    for(int i=0;i<2;i++) deck.push_back(findAnim("Jack-O-Bonnie"));
    for(int i=0;i<2;i++) deck.push_back(findAnim("Jack-O-Chica"));
    for(int i=0;i<3;i++) deck.push_back(findSupport("Freddy Mask"));
    for(int i=0;i<3;i++) deck.push_back(findSupport("William Afton"));
    for(int i=0;i<3;i++) deck.push_back(findSupport("Power Drain"));
    for(int i=0;i<12;i++) deck.push_back(createEnergy());

    shuffleDeck();
    setupInitialHand();

    int op;
    while(true) {
        attachedThisTurn = false;
        cout << "\n--- MENU ---\n";
        cout << "1- Ver mão\n2- Comprar carta\n3- Colocar ativo\n4- Ver ativos / Editar HP\n";
        cout << "5- Usar carta da mão\n6- Ver deck\n7- Usar habilidade de ativo\n8- Descartar carta\n9- Terminar turno\n";
        cin >> op;

        if(op==1) showHand();
        else if(op==2) drawCard();
        else if(op==3) placeActive();
        else if(op==4) editHP();
        else if(op==5) useCard();
        else if(op==6) showDeckContents();
        else if(op==7) useActiveAbility();
        else if(op==8) discardCard();
        else if(op==9) cout << "Turno terminado.\n";
    }

    return 0;
}