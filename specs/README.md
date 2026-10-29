# Dokumentacja SDD projektu

Stan na 2026-10-29. Każdy moduł ma własną specyfikację zachowania, plan techniczny i listę zadań. Najpierw aktualizujemy wymagania, potem plan i zadania, a następnie implementację i dowody weryfikacji.

| Moduł | Stan | Dokumenty | Zadania |
|---|---|---|---|
| 1 — tożsamość i dostęp | Ukończony lokalnie; 265 testów po korekcie sesji | [Specyfikacja](001-identity-access/spec.md), [plan](001-identity-access/plan.md), [zadania](001-identity-access/tasks.md) | E1–E7, T001–T035, 35/35 |
| 2 — ochrona przed botami i wyciekiem danych | E8 w realizacji | [Specyfikacja](002-attack-protection/spec.md), [plan](002-attack-protection/plan.md), [zadania](002-attack-protection/tasks.md), [źródło i decyzje](002-attack-protection/source.md) | E8–E13, T036–T055, 2/20; 2 zadania dodatkowe |

Numeracja etapów i zadań jest ciągła w całym projekcie. Wymagania i kryteria modułu 2 mają prefiks `M2-`, aby nie myliły się z identyfikatorami modułu 1. Moduł 2 rozszerza aplikację i zmienia wskazane zasady logowania; nie otwiera ponownie ukończonych zadań modułu 1.

Najbliższe zadanie: **T038 — panel progu i komunikat czasu blokady**. Podstawowy zakres modułu 2 obejmuje 18 zadań; T050–T051 dotyczą dodatkowej ochrony według adresu IP.

Odbiór modułu 1 opisują [wyniki weryfikacji](../docs/verification.md) oraz [odbiór lokalny](../docs/final-verification.md). Bazą implementacji modułu 2 jest commit `1cf5075`. Brak pushu, wdrożenia lub prób na systemach zewnętrznych.
