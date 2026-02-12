from dataclasses import dataclass, field


@dataclass
class Piece:
    id: int
    x: float    
    y: float    
    classe: int

    def pos(self):
        return (self.x, self.y)

    def __repr__(self):
        return f"P{self.id}(pos=({self.x:.1f},{self.y:.1f})mm, cl={self.classe})"


@dataclass
class Boite:
    classe: int
    position: float

    def __repr__(self):
        return f"Boite(classe={self.classe}, pos={self.position}mm)"


@dataclass
class Plateau:
    largeur: float = 320.0   # mm
    hauteur: float = 320.0   # mm
    boites: dict = field(default_factory=dict)

    def coordonnee_boite(self, classe: int):
        boite = self.boites[classe]
        return (self.largeur, boite.position)

    def distance_au_bord(self, piece: Piece) -> float:
        return self.largeur - piece.x

    def distance_laterale(self, piece: Piece) -> float:
        _, by = self.coordonnee_boite(piece.classe)
        return abs(piece.y - by)

    def distance_totale(self, piece: Piece) -> float:
        bx, by = self.coordonnee_boite(piece.classe)
        return abs(piece.x - bx) + abs(piece.y - by)


def piece_sur_trajet(piece: Piece, autre: Piece, plateau: Plateau, marge: float = 20.0) -> bool:
    
    bx, by = plateau.coordonnee_boite(piece.classe)
    x, y = piece.x, piece.y
    ax, ay = autre.x, autre.y

    y_min, y_max = min(y, by), max(y, by)
    if abs(ax - x) <= marge and y_min - marge <= ay <= y_max + marge:
        return True

    x_min, x_max = min(x, bx), max(x, bx)
    if x_min - marge <= ax <= x_max + marge and abs(ay - by) <= marge:
        return True

    return False


def compter_collisions_chemin(piece: Piece, autres: list, plateau: Plateau) -> int:
    collisions = 0
    for autre in autres:
        if autre.id != piece.id:
            if piece_sur_trajet(piece, autre, plateau):
                collisions += 1
    return collisions


def calculer_priorite(pieces: list, plateau: Plateau) -> list:
    restantes = list(pieces)
    ordre = []

    while restantes:
        candidats = []
        for p in restantes:
            autres = [a for a in restantes if a.id != p.id]
            collisions = compter_collisions_chemin(p, autres, plateau)
            dist_bord = plateau.distance_au_bord(p)
            dist_totale = plateau.distance_totale(p)

            candidats.append({
                "piece": p,
                "collisions": collisions,
                "dist_bord": dist_bord,
                "dist_totale": dist_totale,
            })

        candidats.sort(key=lambda e: (
            e["collisions"],
            e["dist_bord"],
            e["dist_totale"],
        ))

        meilleur = candidats[0]
        ordre.append(meilleur)
        restantes = [p for p in restantes if p.id != meilleur["piece"].id]

    return ordre


def decrire_trajet(piece: Piece, plateau: Plateau) -> str:
    bx, by = plateau.coordonnee_boite(piece.classe)
    x, y = piece.x, piece.y

    dx = bx - x
    dy = by - y

    # Mouvement diagonal : on avance simultanément en X et Y
    # La partie diagonale couvre min(|dx|, |dy|) sur chaque axe
    diag = min(abs(dx), abs(dy))
    reste_x = abs(dx) - diag
    reste_y = abs(dy) - diag

    dir_x = "droite" if dx >= 0 else "gauche"
    dir_y = "bas" if dy > 0 else "haut"

    trajet = f"({x:.1f},{y:.1f})"

    if diag > 0:
        trajet += f" -> diagonale {dir_x}-{dir_y} {diag:.1f}mm"

    if reste_x > 0:
        trajet += f" puis {dir_x} {reste_x:.1f}mm"
    elif reste_y > 0:
        trajet += f" puis {dir_y} {reste_y:.1f}mm"

    trajet += f" -> ({bx:.1f},{by:.1f})"

    return trajet


def afficher_plateau(pieces, plateau):
    L, H = plateau.largeur, plateau.hauteur
    print(f"\n  Plateau {L} x {H} mm  (boîtes côté droit)")
    print(f"  {len(pieces)} pièce(s) :")
    for p in sorted(pieces, key=lambda p: p.id):
        bx, by = plateau.coordonnee_boite(p.classe)
        dist = plateau.distance_totale(p)
        print(f"    {p}  -> boîte cl.{p.classe} à ({bx:.1f},{by:.1f})  dist={dist:.1f}mm")


def executer(pieces: list, plateau: Plateau):
    print("=" * 60)
    print("  ALGORITHME DE PRIORITÉ")
    print("=" * 60)

    afficher_plateau(pieces, plateau)
    ordre = calculer_priorite(pieces, plateau)

    for i, entry in enumerate(ordre, 1):
        p = entry["piece"]
        trajet = decrire_trajet(p, plateau)
        coll = entry["collisions"]
        etat = "libre" if coll == 0 else f"{coll} collision(s)"

        print(f"\n  {i}. {p}")
        print(f"     Trajet : {trajet}")
        print(f"     Dist bord={entry['dist_bord']:.1f}mm | Collisions={coll} | État: {etat}")

    print(f"\n  >>> PREMIÈRE : {ordre[0]['piece']}")
    return [e["piece"] for e in ordre]


def charger_depuis_liste(donnees: list) -> list:
    pieces = []
    for i, item in enumerate(donnees, 1):
        pieces.append(Piece(id=i, x=item[0], y=item[1], classe=item[2]))
    return pieces