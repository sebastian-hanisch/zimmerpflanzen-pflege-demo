"""Die zwölf Pflanzen: Klassen, Streuung der Trockenzeit, Art-Vorwissen (Annahmen, siehe zpf_constants)."""

from dataclasses import dataclass

import numpy as np

import zpf_constants as C


@dataclass(frozen=True)
class Plants:
    cls: np.ndarray        # Klassenindex je Pflanze
    D: np.ndarray          # Tage von voll bis Stressbeginn (Pflanzenwert)
    sstar: np.ndarray      # Stressbeginn
    sw: np.ndarray         # Welkepunkt
    over: np.ndarray       # Fäulnisgrenze (1,0 = keine)
    k: np.ndarray          # Austrocknung je Tag oberhalb des Stressbeginns: (1 - s*) / D
    k_prior: np.ndarray    # Art-Vorwissen: Mittel der Klasse ohne die Streuung der einzelnen Pflanze
    n: int


def make_plants(het=C.HET, seed=C.PLANT_SEED, klassen=C.KLASSEN):
    rng = np.random.default_rng(seed)
    cls, D, ss, sw, so = [], [], [], [], []
    for ci, (_, n, d, a, b, c) in enumerate(klassen):
        for _ in range(n):
            cls.append(ci)
            D.append(d * float(np.exp(rng.normal(0, het))) if het > 0 else d)
            ss.append(a)
            sw.append(b)
            so.append(c)
    cls = np.array(cls)
    D = np.array(D)
    ss, sw, so = np.array(ss), np.array(sw), np.array(so)
    k = (1 - ss) / D
    k_prior = np.array([(1 - klassen[c][3]) / klassen[c][2] for c in cls])
    return Plants(cls=cls, D=D, sstar=ss, sw=sw, over=so, k=k, k_prior=k_prior, n=len(cls))


def class_mask(plants, class_index):
    return plants.cls == class_index
