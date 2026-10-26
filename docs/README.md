# Specyfikacje telemetrii UDP (EA)

Oficjalne dokumenty z forum EA (F1 Game Info Hub). Parsery w `boxbox/telemetry/`
są sprawdzone z plikami `*_Telemetry_Output_Structures.txt` (formaty 2025 i 2026).

- `Data_Output_from_F1_25_v3.pdf`, `F1_25_Telemetry_Output_Structures.txt` – F1 25, wersja 3.
- `Data_Output_from_F1_25_2026_Season_Pack*.pdf`, `2026_Season_Pack_Telemetry_Output_Structures.txt`
  – dodatek 2026 Season Pack: format pakietu 2026, 24 auta, inne rozmiary pakietów,
  nowy pakiet Car Telemetry 2 (id 16). Obsługiwany równolegle z 2025; parser wybiera
  układ po polu `packetFormat` w nagłówku.

Różnice 2026 względem 2025 w pakietach, które czytamy:
- Session: +173 B na końcu (strefy aktywnego aero i DRS, czas reakcji na starcie, asysty ABS/TC).
- Car Telemetry: temperatura silnika uint8 zamiast uint16.
- Car Status: +ersHarvestLimitPerLap (float); tryb ERS 3 to "boost".
- Event: kolizja (COLL) ma dodatkowo wagę.
- Lap Data, Car Damage: tylko liczba aut.
- Car Telemetry 2: nowy pakiet (aktywne aero, overtake, jazda pod prąd).

Źródło: https://forums.ea.com/blog/f1-games-game-info-hub-en/f1%c2%ae-25-udp-specification/12187347
