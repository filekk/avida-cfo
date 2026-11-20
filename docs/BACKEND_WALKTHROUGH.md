# Avida CFO – przewodnik po backendzie + code review

Dla zespołu backendu. Czytaj od góry: najpierw obraz całości, potem plik po pliku, na końcu znane ryzyka.

---

## 1. Obraz całości

```
Przeglądarka (Vue)                     FastAPI  (backend/app/main.py)                     OpenShift AI
──────────────────                     ─────────────────────────────                     ────────────
GET  /api/dashboard ─────────────────► initial_dashboard()  ── prognoza bez maili
GET  /api/sync  (SSE) ───────────────► orchestrator.run_pipeline()  ──── async generator ─┐
   ◄── event: trace  (krok agenta)       │                                               │
   ◄── event: trace  (handoff A → B)     ├─ analyst.read_email()   ×6 równolegle ────────┼──► vLLM / Granite 3.3 8B
   ◄── …                                 ├─ legal.check()          ×5 równolegle ────────┤    (OpenAI-compatible API,
   ◄── event: result (cały dashboard)    ├─ analyst.forecast()     deterministycznie     │     guided JSON)
                                         ├─ _negotiate()           ×3 równolegle ────────┤
POST /api/actions/{id}/approve ──────► store.decide()  → symulacja, licznik "Saved"      │
POST /api/reset ─────────────────────► store.reset()                                     │
```

**Trzy zasady projektu** (warto je powtarzać na pitchu):
1. **LLM nigdy nie liczy.** Wszystkie kwoty, daty, salda i kredyt liczy Python (`forecast.py`, `analyst.py`).
   LLM tylko czyta maile, wyjaśnia i pisze.
2. **Werdykt prawny dają reguły, nie model.** `legal.rule_checks()` / `payment_checks()` decydują; LLM tylko
   tłumaczy werdykt prostym językiem i wybiera klauzulę do zacytowania (a cytat jest sprawdzany).
3. **Każde wywołanie LLM ma fallback.** Model padnie lub zwróci śmieci → gotowa odpowiedź z `fallback.py`,
   oznaczona `source: "fallback"` (UI pokazuje „cached answer”). Demo przeżyje awarię modelu.

---

## 2. Plik po pliku

### `config.py` – konfiguracja
Wszystko z env (na klastrze z ConfigMap `avida-cfo-config`). Najważniejsze:
`LLM_BASE_URL`, `LLM_MODEL=granite-8b`, `LLM_TIMEOUT_S=60`, `LLM_ENABLED` (false = zawsze fallback, tak chodzą testy),
`DEMO_FALLBACK` (false = błąd modelu wywala pipeline – do debugowania), `DEMO_TODAY=2026-11-20` (stała data → demo
zawsze liczy to samo), `TRACE_DELAY_S=0.4` (pauza między krokami, żeby widownia nadążyła).
⚠️ Wartości czytane są przy imporcie – zmiana env wymaga restartu.

### `data.py` + `backend/data/` – źródła danych (mock)
- `company.json` – firma, saldo 93 000, poduszka 15 000, oferta kredytu (9,5%, krok 5 000).
- `cashflows.json` – stałe miesięczne wpływy/wydatki (`recurring_monthly`, dzień miesiąca) + jednorazowe (`one_off`).
  **`counterparty` musi być identyczny z nazwą w umowie**, inaczej podwyżka/opóźnienie nie trafi w prognozę.
- `inbox_mock.json` – 6 maili demo.
- `contracts_index.json` – umowy w formie strukturalnej: klauzule + pola dla reguł (`fixed_price_until`,
  `price_change_notice_days`, `max_annual_increase_pct` dla dostawców; `payment_terms_days`,
  `changes_require_written_agreement` dla klientów – klient ma klucz `customer` zamiast `supplier`).
- `contracts/*.md` – teksty umów (notebook robi z nich PDF-y). Umowy z klientami są w `contracts/customers/`,
  bo notebook zakłada umowy z dostawcami i globuje tylko `contracts/*.md`.

Loadery mają `@lru_cache` → zmiana JSON-a wymaga restartu.

### `llm.py` – klient modelu
`AsyncOpenAI` wskazany na vLLM, `max_retries=0` (zamiast retry jest fallback, demo nie może wisieć).
- `json(system, user, schema, fallback)` – **structured output**: vLLM wymusza schemat JSON (guided decoding),
  więc model fizycznie nie może zwrócić złego kształtu. Zwraca `(wynik, "llm" | "fallback")`.
- `text(system, user, fallback)` – zwykły tekst (maile).
- Fallback jest zwracany jako `deepcopy` (poprawka z review – patrz §5).

### `forecast.py` – silnik prognozy (czysty Python, zero LLM)
- `expand_items()` rozwija definicje na konkretne dni w horyzoncie 90 dni i stosuje:
  - `Adjustment` – podwyżka: od daty `effective` pozycja dostawcy jest droższa o `monthly_delta`;
  - `Delay` – opóźniona płatność: wpływ klienta najbliższy `due` (±3 dni) przenoszony na `new_date`
    (a jeśli wypada poza horyzont – znika z prognozy).
- `run_forecast()` – saldo dzień po dniu, minimum, pierwszy/ostatni dzień pod poduszką, `days_safe`.
- `size_credit_line()` – luka = poduszka − minimum, zaokrąglona w górę do kroku 5 000; maks. odsetki =
  kwota × stopa × dni / 365 (górne oszacowanie: cała kwota przez cały okres).

### `agents/analyst.py` – 📊 Analyst Agent
1. **`read_email()`** – LLM klasyfikuje mail: `price_change` / `payment_delay` / `other` i wyciąga liczby
   (jeden schemat JSON dla wszystkich rodzajów). Potem **`sanitize()`** – najważniejszy strażnik w projekcie:
   - każda kwota musi **występować w treści maila** (`amounts_in()` czyta format angielski `9,800.00`
     i niemiecki `14.000,00`); wymyślona kwota → `figures_stated: false`,
   - daty muszą się parsować, opóźnienie musi być > 0 dni,
   - procent i różnicę liczy Python (model mógłby się pomylić),
   - sufiks działu („Stahlhandel Nord GmbH – Vertrieb”) jest obcinany.
   `figures_stated: false` znaczy: **nie liczymy, pytamy** (przypadek IT-Service Kraus).
2. **Liczby:** `forecast()`, `impact()` (koszt podwyżki w horyzoncie i rocznie), `delay_impact()` (o ile opóźnienie
   obniża najniższe saldo: prognoza z opóźnieniem vs bez), `credit_proposal()`, `headline()`.
3. **Briefing:** `_facts()` buduje deterministyczne zdania (`key_points` – zawsze poprawne), m.in. wykrywa
   **największą płatność w dniu, gdy konto byłoby na minusie** (wypłata 28.01). LLM dostaje tylko 3 pierwsze fakty
   i pisze `summary`; `summary_ok()` odrzuca tekst dłuższy niż 3 zdania / 320 znaków albo zawierający liczbę,
   której nie ma w faktach → wtedy deterministyczny headline.

### `agents/legal.py` – ⚖️ Legal Agent
1. **`check()`** – jeden punkt wejścia dla każdego znaleziska:
   - `find_contract()` – po nazwie i aliasach (pusta nazwa nigdy nie pasuje – poprawka z review),
   - normalizuje nazwę kontrahenta do nazwy z umowy (żeby prognoza trafiła we właściwą pozycję),
   - brak umowy albo brak liczb → `verdict: "unclear"` bez pytania modelu (`source: "rules"`),
   - reguły: `rule_checks()` (gwarancja ceny, okres wypowiedzenia, limit roczny) lub `payment_checks()`
     (termin płatności, zakaz jednostronnej zmiany),
   - **jakakolwiek reguła złamana → `violates`**, inaczej `allowed`,
   - LLM pisze wyjaśnienie i wybiera klauzulę; **cytat musi dosłownie istnieć w umowie** (pierwsze 40 znaków),
     inaczej podmieniamy na prawdziwą klauzulę.
2. **`review_draft()`** – zasada czterech oczu dla maili Negocjatora:
   - `rule_review()` (deterministycznie, zależnie od zadania): jest numer klauzuli, jest kwota (cena umowna /
     kwota faktury), brak `[placeholderów]`, brak zdradzania własnych finansów (EN + DE: liquidity, cash flow,
     overdraft, Liquidität, Engpass, Kontokorrent…),
   - plus opinia LLM (max 2 uwagi). Uwagi → Negocjator poprawia raz → Legal sprawdza ponownie.

### `agents/negotiator.py` – ✉️ Negotiator Agent
Trzy zadania z osobnymi promptami: `reject_price` (stanowczo), `payment_reminder` (ciepło, ważny klient!),
`ask_details` (prośba o liczby). `_brief()` składa wejście z sekcji `[from Analyst Agent]` i `[from Legal Agent]`
– to jest „współpraca agentów” w danych, nie tylko w UI. Fallback = szablony z `fallback.py`, które **gwarantowanie
przechodzą** `rule_review()` (sprawdzane w testach).

### `orchestrator.py` – dyrygent
`run_pipeline()` to async generator – każdy `yield` = jedno zdarzenie SSE. Kolejność:
1. Analyst czyta wszystkie maile **naraz** (`asyncio.gather` → vLLM batchuje) → handoff do Legal.
2. Legal sprawdza wszystkie zmiany naraz → werdykty z powrotem do Analityka.
3. Analyst liczy 3 scenariusze (patrz §3) + wpływ każdego znaleziska + kredyt.
4. Briefing startuje w tle (`create_task`).
5. **Negocjacje równolegle:** każde znalezisko z zadaniem (`reject`/`remind`/`review`+price) dostaje własny task
   `_negotiate()`; zdarzenia płyną przez `asyncio.Queue`, więc UI widzi je na żywo, przeplecione.
   Dzięki temu 3 maile trwają tyle co 1 (~27 s cały pipeline na L4).
6. Akcje tworzone **w kolejności skrzynki** (stabilne `act-1…act-4`), potem kredyt, potem briefing, potem `result`.
- `_running` – drugi sync w trakcie pierwszego dostaje błąd (inaczej `store.reset()` skasowałby akcje pierwszego).
- `finally` anuluje zadania w tle, gdy przeglądarka się rozłączy (`main.py` używa `aclosing`).

### `state.py` – stan w pamięci
`Store`: akcje, audit log, licznik `saved_liquidity`. `decide()` – approve wykonuje **symulację** (`_simulate`),
nic nie wychodzi z systemu. `POLICY` – macierz autonomii (kto co może) dla `/api/policy`.

### `main.py` – API
Endpointy z `docs/API.md`, SSE na `/api/sync`, serwowanie zbudowanego Vue z `STATIC_DIR` (SPA fallback na `index.html`).

### `ask.py` – „Ask your CFO” (`/api/ask`, `/api/ask/suggestions`)
Właściciel pyta prostym językiem, odpowiada właściwy agent – **tylko z liczb już policzonych** (nic nowego nie liczymy).
1. **Fakty per agent** (`analyst_facts` / `legal_facts` / `negotiator_facts`) – zdania po angielsku z dokładnymi
   liczbami z dashboardu (przed syncem: sama prognoza). Agent dostaje tylko swoje fakty.
2. **Router** (`route`) – deterministyczny, po słowach EN+DE (całe słowa: „Briefing” ≠ „Brief”); domyślnie Analityk.
   Kliknięta podpowiedź ma agenta przypisanego z góry.
3. **Podpowiedzi** (`suggestions`) – generowane z sytuacji (kredyt, opóźniony klient, odrzucona podwyżka, mail bez
   liczb, „czy jestem bezpieczna”, największe płatności), w EN albo DE, stała kolejność, max 4. Każda ma **gotową
   odpowiedź** w tym języku (niemiecki format liczb i dat) – nie wychodzi do frontendu, służy jako fallback.
4. **Kliknięta podpowiedź** → od razu gotowa odpowiedź (`source: "rules"`, bez LLM). Powód: test na żywo pokazał,
   że Granite 8B po niemiecku potrafi przekręcić sens przy prawdziwych liczbach, a tego strażnik nie łapie.
5. **Pytanie wpisane ręcznie** (`ask`) – LLM zwraca `{answer, in_data}`:
   - `in_data=false` → stała uprzejma odmowa (EN/DE) + podpowiedzi,
   - `answer_ok()` – max 4 zdania / 500 znaków, każda liczba (także `27.882`, `9,5 %`, `03.02.2027`) musi być w faktach,
   - strażnik odrzucił / model padł → „nie jestem pewna…” + gotowa odpowiedź pierwszej podpowiedzi tego agenta.
Każde pytanie trafia do audit logu.

---

## 3. Przebieg demo w liczbach (offline i na żywym Granite wychodzi to samo)

| Krok | Wynik |
|---|---|
| Przed syncem | min. saldo **11 000** EUR 03.02.2027, 73 dni bezpiecznie |
| CloudHost +15% | §5.2 gwarancja do 31.08.2027 + 42 zamiast 90 dni wypowiedzenia → **reject**, 17 640 EUR/rok |
| PaperPro +3,5% | limit 5%, 42 dni wypowiedzenia ≥ 30 → **accept**, 504 EUR/rok |
| Stahlhandel +6% (DE) | limit 8%, 44 dni ≥ 42 → **accept**, 10 080 EUR/rok |
| Bauer: 38 000 EUR 30 dni później | §7.1 + §7.2 → **remind**; najniższe saldo niższe o 38 000 |
| Kraus: „podwyżka”, bez liczb | **review**, nic nie liczymy, Negocjator pyta o ceny |
| Scenariusz `recommended` | dozwolone podwyżki + opóźnienie Bauera (planujemy ostrożnie) → **−27 882** EUR 03.02, wypłata 28.01 niepokryta |
| Scenariusz `if_accepted` | wszystkie podwyżki + opóźnienie → **−29 352** EUR |
| Kredyt | luka 42 882 → **45 000** EUR, 22.01–04.02 (14 dni), maks. **164** EUR odsetek |

Uwaga do nazw scenariuszy: `recommended` = „robisz to, co radzi Avida, ale planujemy ostrożnie, że Bauer zapłaci
późno” (nie możemy klienta zmusić). `if_accepted` = „akceptujesz wszystko”.

---

## 4. Gdzie model mógłby zmyślić i co go łapie

| Ryzyko | Strażnik | Gdzie |
|---|---|---|
| Model wymyśla kwotę w ekstrakcji | kwota musi być w treści maila (EN/DE) | `analyst.sanitize` |
| Model źle liczy procent | procent/różnica liczone w Pythonie | `analyst.sanitize` |
| Zła data / „January” zamiast ISO | parsowanie, inaczej `figures_stated: false` | `analyst._iso` |
| Zła nazwa firmy („– Billing”) | obcięcie sufiksu + normalizacja do nazwy z umowy | `sanitize`, `legal._normalise` |
| Model „orzeka” inaczej niż umowa | werdykt z reguł, model dostaje go jako „fixed” | `legal.check` |
| Zmyślony cytat z umowy | cytat musi istnieć w tekście klauzuli | `legal.check` |
| Mail zdradza problemy finansowe | regex EN+DE + review LLM | `legal.rule_review` |
| Mail bez klauzuli / kwoty / z [Name] | reguły + jedna runda poprawek | `legal.rule_review`, orchestrator |
| Briefing z wymyśloną liczbą | liczby ⊆ fakty, max 3 zdania / 320 znaków | `analyst.summary_ok` |
| Odpowiedź na pytanie z wymyśloną liczbą | liczby ⊆ fakty agenta (EN+DE), max 4 zdania | `ask.answer_ok` |
| Pytanie spoza danych firmy | `in_data=false` → stała odmowa | `ask.ask` |
| Model nie działa | fallback + etykieta `fallback` | `llm.py`, `fallback.py` |

---

## 5. Code review – co znalazłem i co z tym zrobiłem

### Naprawione w tej zmianie
| # | Problem | Skutek | Poprawka |
|---|---|---|---|
| 1 | Fallback zwracany przez referencję i potem mutowany (`_sanitize`, normalizacja nazwy) | kolejne przebiegi dostawały zmienione „gotowe odpowiedzi” | `deepcopy` w `llm.py` + test |
| 2 | `find_contract("")` pasowało do **pierwszej umowy** (`"" in "cloudhost gmbh"` = True) | mail z pustym dostawcą zostałby oceniony umową CloudHost | pusta nazwa → `None` + test |
| 3 | Zła/pusta data od modelu → `date.fromisoformat` wywalał **cały pipeline** | błąd SSE w trakcie demo | walidacja dat w `sanitize` |
| 4 | Brak walidacji kwot z modelu | wymyślona kwota szłaby do prognozy | kwoty muszą być w mailu |
| 5 | Dwa równoczesne `/api/sync` (podwójny klik, dwie karty) | drugi `store.reset()` kasował akcje pierwszego, mieszane ID | flaga `_running` + test |
| 6 | Rozłączenie przeglądarki zostawiało zadanie briefingu w tle | wiszące wywołania LLM, ostrzeżenia | `aclosing` + `cancel()` w `finally` |
| 7 | `impact()` liczył płatności po `d.day == pay_day`, a prognoza przycina dzień 30/31 do końca miesiąca | dla płatności 30./31. niezgodność z prognozą (luty) | wspólna funkcja `pay_date()` |
| 8 | Cashflow „Stahlhandel Nord” ≠ umowa „Stahlhandel Nord GmbH” | podwyżka nie trafiłaby w prognozę | ujednolicona nazwa |
| 9 | Briefing LLM przy 9 faktach przekręcał sens (twierdził, że odrzucenie *dozwolonych* podwyżek oszczędza pieniądze) | fałszywa informacja dla właściciela | 3 fakty + limit długości; `key_points` zawsze deterministyczne |
| 10 | Negocjacje sekwencyjnie | każdy kolejny mail +10–15 s | równolegle przez kolejkę |

### Znane ograniczenia (świadomie zostawione na hackathon)
| Waga | Problem | Kiedy boli | Co zrobić, jeśli będzie czas |
|---|---|---|---|
| 🟠 | Stan w pamięci procesu | >1 replika albo restart poda = akcje znikają, approve trafia do innego poda | trzymać `replicas: 1`; ewentualnie Redis |
| 🟠 | Brak autoryzacji API | każdy z URL-em route'a może zrobić approve/reset | na demo OK; nie wrzucać linku publicznie |
| 🟡 | Edytowany przez właściciela mail omija review Prawnika | właściciel może wpisać „mamy problem z płynnością” | puścić `rule_review` na `edited_body` i pokazać ostrzeżenie |
| 🟡 | `summary` LLM może nadal źle oddać sens (strażnik sprawdza tylko liczby) | rzadko, przy 3 faktach nie zaobserwowane | na pitch można przełączyć na deterministyczne |
| 🟡 | `rule_review` sprawdza kwotę jako podciąg wszystkich cyfr maila | teoretycznie fałszywe „OK” | szukać kwoty jako liczby (jak `amounts_in`) |
| 🟡 | Kredyt przy dwóch osobnych oknach pod poduszką liczy okres od pierwszego do ostatniego dnia | zawyżone dni/odsetki (to i tak górne oszacowanie) | liczyć okna osobno |
| ⚪ | `Delay` dopasowuje wpływ po kontrahencie ±3 dni, nie po kwocie | dwie wpłaty od jednego klienta w 3 dni | dopasować też po kwocie |
| ⚪ | Umowa bez pól reguł → zawsze `allowed` | nowa umowa bez danych | domyślnie `unclear` |
| ⚪ | Retrieval klauzul po słowach kluczowych (podciągi) | duże umowy | embeddingi / ChromaDB |
| ⚪ | `CORS *` | – | zawęzić po demo |

---

## 6. Jak uruchomić, testować, debugować

```bash
cd backend
# testy (offline, fallback) – 14 testów, ~2 s
PYTHONIOENCODING=utf-8 .venv/Scripts/python -m pytest -q

# pipeline na żywym modelu z laptopa
oc -n avida-models port-forward deploy/granite-8b-predictor 8001:8080     # osobny terminal
LLM_BASE_URL=http://localhost:8001/v1 uvicorn app.main:app --port 8080 --reload
# → http://localhost:8080/docs  (Swagger),  GET /api/sync w przeglądarce pokaże surowy strumień SSE

# debug: niech błąd modelu wywali pipeline zamiast cicho użyć fallbacku
DEMO_FALLBACK=false LLM_BASE_URL=… uvicorn app.main:app --port 8080
```
Na klastrze: `oc -n avida-cfo logs deploy/avida-cfo -f` – ostrzeżenia `LLM json failed: …` mówią, który krok
spadł na fallback.

## 7. Gdzie dopisywać nowe rzeczy
- **Nowy mail demo:** `inbox_mock.json` + gotowa odpowiedź w `fallback.EXTRACTIONS` (format surowy jak z LLM)
  + (jeśli ma umowę) wpis w `contracts_index.json` + `counterparty` w `cashflows.json` identyczny z umową.
- **Nowa reguła prawna:** pole w `contracts_index.json` + sprawdzenie w `legal.rule_checks` / `payment_checks`.
- **Nowy rodzaj maila:** `kind` w `EXTRACT_SCHEMA` → gałąź w `sanitize` → `legal.check` → `RECOMMEND` i `_task`
  w orchestratorze → prompt + szablon w negotiatorze → reguły w `rule_review`.
- **Nowy endpoint (np. `/api/ask`):** `main.py`; liczby brać z `store.dashboard`, odpowiedź przepuścić przez
  `summary_ok()`-podobnego strażnika.
