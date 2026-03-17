from dataclasses import dataclass, field


@dataclass #generation automatique de méthode spéciales comme __init__ ou __repr__
class Piece:
    id: int #identifiant unique de la pièce 
    x: float    
    y: float    
    classe: int #type de piièce

    def pos(self):
        return (self.x, self.y)

    def __repr__(self): #DEBUG sous forme de chaine
        return f"P{self.id}(pos=({self.x:.1f},{self.y:.1f})mm, cl={self.classe})"


@dataclass #generation automatique de méthode spéciales comme __init__ ou __repr__
class Boite:
    classe: int
    position: float

    def __repr__(self): #DEBUG sous forme de chaine
        return f"Boite(classe={self.classe}, pos={self.position}mm)"


@dataclass 
class Plateau:
    largeur: float = 320.0   # mm
    hauteur: float = 320.0   # mm
    boites: dict = field(default_factory=dict) #à chaque instance de la classe, on créée un nouveau dictionnaire

    def coordonnee_boite(self, classe: int):
        boite = self.boites[classe] #dictionnaire appartenant à cet instance
        return (self.largeur, boite.position) #largeur : coordonée x, boite.position : corrdonée y

    def distance_au_bord(self, piece: Piece) -> float:
        return self.largeur - piece.x 

    def distance_laterale(self, piece: Piece) -> float:
        _, by = self.coordonnee_boite(piece.classe) #coordonée y de la boite
        return piece.y - by #de combien je dois bouger pour arriver devant la boite ( + : bouger vers le bas / - : bouger vers le haut)

    def distance_totale(self, piece: Piece) -> float: #pas DE, somme des chemins parcourus en x puis en y
        bx, by = self.coordonnee_boite(piece.classe)
        return abs(piece.x - bx) + abs(piece.y - by) 


def piece_sur_trajet(piece: Piece, autre: Piece, plateau: Plateau, marge: float = 20.0) -> bool:
    """ Vérifie si une pièce est sur le trajet pour éviter la collision

    Args:
        piece (Piece): pièce en déplacement
        autre (Piece): Autre pièce avec laquelle la pièce déplacée peut entrer en collision
        plateau (Plateau): Instance de la classe Plateau 
        marge (float, optional): Marge d'évitement en mm (défaut : 20mm)

    Returns:
        bool: True : Collision / False : Pas de collision
    """
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

        candidats.sort(key=lambda e: (e["dist_bord"],e["collisions"], e["dist_totale"],)) #d'abord la pièce la plus proche du bord, ensuite celle avec le moins de collisions, ensuite celle la plus loin

        meilleur = candidats[0]
        ordre.append(meilleur)
        restantes = [p for p in restantes if p.id != meilleur["piece"].id]

    return ordre


def decrire_trajet(piece: Piece, plateau: Plateau) -> str:
    bx, by = plateau.coordonnee_boite(piece.classe)
    x, y = piece.x, piece.y

    dx = bx - x
    dy = by - y

    dir_x = "droite" if dx >= 0 else "gauche"
    dir_y = "bas" if dy > 0 else "haut"

    trajet = f"({x:.1f},{y:.1f})"

    # D'abord le mouvement horizontal (axe X)
    if abs(dx) > 0:
        trajet += f" -> {dir_x} {abs(dx):.1f}mm"

    # Puis le mouvement vertical (axe Y)
    if abs(dy) > 0:
        trajet += f" puis {dir_y} {abs(dy):.1f}mm"

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