# Dev Agent Workflow

Plugin Codex CLI prowadzący od analizy aplikacji lub featura do przetestowanych
zmian i draft PR. Główny orchestrator deleguje zadania natywnym agentom.
Komunikacja z użytkownikiem jest po polsku, materiały robocze po angielsku.

## Instalacja

Wymagania: Codex CLI z pluginami i natywnymi agentami (implementacja przygotowana
dla `0.154.0`), Python 3.10+, Git i zalogowane `gh` do publikacji.
Modele muszą być dostępne w Twoim abonamencie Codex. Plugin nie wymaga klucza API.

```sh
gh repo clone Jared0o/dev-agent-workflow
cd dev-agent-workflow
python3 scripts/validate.py
python3 scripts/install.py
```

Instalator tworzy symlink `~/plugins/dev-agent-workflow` do tego checkoutu,
rejestruje wpis w osobistym `~/.agents/plugins/marketplace.json` i wywołuje
`codex plugin add`. Zachowuje inne wpisy i odmawia nadpisania innej instalacji.
`--register-only` pomija wywołanie Codex. Instalacja zapisuje pliki w katalogu
domowym — sandbox może wymagać uprawnienia do tej operacji.
Osobisty marketplace jest wykrywany automatycznie; nie trzeba go dodawać osobnym
`codex plugin marketplace add`.

Uruchom nową sesję w katalogu aplikacji:

```sh
codex -m gpt-6-astra -c 'model_reasoning_effort="high"'
```

Następnie wpisz:

```text
$dev-workflow Dodaj logowanie do aplikacji Go + Next.js. Najpierw przygotuj analizę.
$dev-workflow Pokaż status zadania add-login.
$dev-workflow Wznów zadanie add-login.
```

Skill nie zmienia modelu sesji głównej. W trwającej sesji wybierz go przez `/model`.
Nazwy modeli i poziomy rozumowania są sprawdzane przez środowisko Codex; przy
niedostępności workflow zatrzymuje delegowanie i prosi o wybór zamiennika.

## Przebieg

| Etap | Model domyślny | Wynik |
|---|---|---|
| Analiza | GPT-6 Astra / high | Specyfikacja, architektura, kontrakty i zadania do Twojej akceptacji |
| Implementacja | GPT-5.6 Terra / medium | Kod i testy w przypisanym zakresie |
| Testy | GPT-5.6 Terra / medium | Wyniki narzędzi i ocena scenariuszy akceptacyjnych |
| Review | GPT-6 Astra / high | Niezależna ocena poprawności, zgodności i bezpieczeństwa |
| Dokumentacja | GPT-5.6 Luna / low | Dokumentacja i podsumowanie; orchestrator publikuje draft PR |

Po akceptacji analizy dalsza praca przebiega samodzielnie w ustalonym zakresie.
Zmiana zakresu lub kontraktu wraca do użytkownika. Drobne poprawki mają krótsze
etapy, jednego wykonawcę i odpowiednio ograniczone kontrole.

Profile obejmują Go, C#/.NET i React/Next.js. Korzystają z narzędzi i wersji
zastanego projektu. REST/OpenAPI lub gRPC/protobuf wybierane są podczas analizy;
plugin nie narzuca architektury ani CMS. Do trzech pomocniczych agentów może
pracować równolegle, jeżeli zakresy są niezależne. Wspólne kontrakty i lockfile
mają jednego właściciela. Tylko orchestrator wykonuje operacje Git i publikuje.

## Konfiguracja i stan

Domyślne ustawienia są w [config/defaults.json](config/defaults.json).
Opcjonalny plik aplikacji `.dev-workflow/config.json` zawiera tylko nadpisania:

```json
{
  "max_parallel_agents": 2,
  "models": {
    "implementer": {"model": "gpt-5.6-terra", "effort": "high"}
  }
}
```

Domyślnie dopuszczone są dwie rundy naprawy problemu i jedna próba po diagnozie
mocniejszego modelu. Ustawienie `delivery: "local"` kończy pracę lokalnym commitem.
Modelowe role, limity prób i równoległości można zmieniać w konfiguracji;
zmiana konfiguracji w trakcie zadania wymaga ponownego zaakceptowania planu.

`.dev-workflow/tasks/<id>/` przechowuje specyfikację, graf zadań, stan, raporty
i informacje o publikacji. Orchestrator dodaje `.dev-workflow/` do ignorowanych
plików aplikacji. Zawartość nie trafia do PR. Zapis umożliwia wznowienie w nowej
sesji; repozytoryjne zmiany i raporty są porównywane przez SHA-256.

[Opis poleceń i formatu stanu](skills/dev-workflow/references/state.md)
wyjaśnia akceptację, kontrolę zależności, zapisywanie wyników i wznowienie.
Helpery są lokalnymi narzędziami walidacji, nie silnikiem uruchamiającym modele.
Nie potwierdzają samodzielnie, że człowiek zaakceptował plan lub że test wykonano:
orchestrator musi zapisywać rzeczywiste wyniki narzędzi. Podmoduły wymagają osobnych
workflow; zmiany w ignorowanych zależnościach i zewnętrznych usługach trzeba
uwzględnić w ocenie aktualności wyników.

## Oszczędność i jakość

Agenci otrzymują krótkie pakiety zadań i odnośniki do potrzebnych plików zamiast
pełnej historii. Testy wykonują narzędzia projektu, a model ocenia ich wyniki
i sensowność scenariuszy. Ponawiane są kontrole dotknięte zmianą; zachowanie
poprzednich wyników po zmianie samej dokumentacji wymaga uzasadnionej oceny delty.
Review i wymagane testy blokują publikację, jeżeli nie zostały wykonane lub wykryły
nierozwiązany problem. Brak narzędzia nie oznacza wyniku pozytywnego.

Podsumowanie podaje rzeczywistą liczbę agentów/prób i tokeny, jeżeli runtime je
udostępnia. Plugin nie odczytuje sekretów ani prywatnych logów sesji w celu pomiaru.
Nie obiecuje procentowej oszczędności ani przeliczenia tokenów na limit abonamentu.
Równoległość skraca czas części zadań, ale może zwiększać zużycie tokenów.

## GitHub i wersje

Repozytorium tego pluginu i nowo tworzone repozytoria aplikacji są prywatne.
W istniejących projektach zachowana jest widoczność repozytorium — gałąź nie ma
osobnego ustawienia prywatności. Domyślny rezultat to zwykły push gałęzi i draft PR,
bez automatycznego merge, wdrożenia czy wysyłania wiadomości do innych osób.
Brak dostępu do GitHub pozostawia gotowe zmiany lokalnie do wznowienia publikacji.

Wersjonowanie: SemVer w manifeście i tagach `v0.1.0`, `v0.2.0` itd.
Aktualizacja instalacji po opublikowanym wydaniu:

```sh
git pull --ff-only
python3 scripts/validate.py
python3 scripts/install.py
```

Rozpocznij nową sesję po reinstalacji. Przy lokalnym rozwoju tej samej wersji użyj
narzędzia `update_plugin_cachebuster.py` z umiejętności `plugin-creator`, jeśli jest
dostępna, i ponownie zainstaluj plugin; nie edytuj ręcznie istniejącego marketplace.
Wydania używają normalnej nowej wersji SemVer.

## Weryfikacja pluginu

```sh
python3 scripts/validate.py
python3 -m unittest discover -s tests -v
```

Testy są lokalne, oparte na bibliotece standardowej i tymczasowych repozytoriach.
Nie uruchamiają płatnych modeli i nie publikują do GitHub. Walidacja struktury
nie zastępuje oceny zachowania agentów; scenariusze do prób z Codex znajdują się
w [tests/scenarios.md](tests/scenarios.md).

Podstawy integracji: [natywni agenci Codex](https://learn.chatgpt.com/docs/agent-configuration/subagents),
[pluginy](https://learn.chatgpt.com/docs/plugins),
[dobór i zachowanie GPT-6 Astra](https://developers.openai.com/api/docs/guides/latest-model).
