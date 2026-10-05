# 🎮 CLARA - Comece a Jogar Agora!

## ⚡ Início Rápido (3 passos)

### 1. Instalar Pygame
```bash
pip install pygame
```

### 2. Rodar o Jogo

**OPÇÃO A - Usando o Launcher (Menu bonito):**
```bash
python launcher.py
```
Isso abre um menu onde você pode escolher qual versão jogar.

**OPÇÃO B - Rodar diretamente a versão original:**
```bash
python clara_game.py
```

**OPÇÃO C - Rodar a versão melhorada:**
```bash
python clara_game_enhanced.py
```

---

## 🎯 Qual Versão Escolher?

| | Original | Melhorada |
|---|----------|-----------|
| **Tamanho** | Compacto | Completo |
| **Áudio** | Não | Sim ✅ |
| **Gráficos** | Simples | Avançados ✅ |
| **Cinemáticas** | Não | Sim ✅ |
| **Saves** | Não | Sim ✅ |
| **Configurações** | Não | Sim ✅ |
| **Recomendado** | Aprender | Jogar ✅ |

**👉 Recomendação: Versão Melhorada (`clara_game_enhanced.py`)**

---

## 🎮 Controles Básicos

| Tecla | O quê faz |
|-------|-----------|
| **WASD** ou **Setas** | Andar |
| **ESPAÇO** | Se esconder / Interagir |
| **P** | Pausar |
| **ESC** | Abrir menu / Sair |

No final do jogo:
- **E** = Contar a verdade
- **S** = Ficar em silêncio

---

## 📁 Arquivos Criados

```
projeto/
├── launcher.py                   ← Comece daqui!
├── clara_game_enhanced.py        ← Versão completa
├── clara_game.py                 ← Versão original
├── audio_manager.py              ← Sistema de som
├── graphics_engine.py            ← Gráficos avançados
├── cinematics.py                 ← Cinemáticas
├── save_manager.py               ← Salvamento
├── config.py                     ← Configurações
├── requirements.txt              ← Dependências
├── START_AQUI.md                 ← Este arquivo
├── COMO_USAR.md                  ← Guia detalhado
├── README_MELHORIAS.md           ← Documentação completa
└── assets/                       ← Sons (opcional)
    └── audio/
        ├── music/
        └── sfx/
```

---

## 🎮 Como Jogar

### Fase 1: Exploração
1. Acorda de madrugada (03:17)
2. Casa escura, barulhos estranhos
3. **Objetivo:** Procure por pistas (círculos amarelos)
4. Leia bilhetes, encontre fotos, descubra segredos

### Fase 2: Perseguição
1. Após encontrar 2 pistas, perseguição começa
2. Uma figura misteriosa aparece
3. **Objetivo:** Se esconda em locais seguros (quadrados verdes)
4. Ou corra até conseguir escapar

### Fase 3: Escolha Final
1. Clara consegue sair de casa
2. **Escolha:**
   - **E**: Contar para alguém (Bom Final)
   - **S**: Ficar em silêncio (Final Sombrio)

---

## 🎵 Adicionar Áudio (Opcional)

Se quer som no jogo:

1. Crie a pasta:
```bash
mkdir -p assets/audio/music
mkdir -p assets/audio/sfx
```

2. Adicione arquivos `.wav` com estes nomes:
   - `assets/audio/music/intro.wav`
   - `assets/audio/music/exploring.wav`
   - `assets/audio/music/chase.wav`
   - `assets/audio/sfx/clue_found.wav`
   - `assets/audio/sfx/scare.wav`

*(Sem os arquivos de som, o jogo ainda funciona normalmente)*

---

## 🔧 Solução de Problemas

### "ModuleNotFoundError: No module named 'pygame'"
```bash
pip install pygame
```

### "Arquivo não encontrado"
Verifique se está executando do diretório certo:
```bash
cd caminho/do/projeto
python launcher.py
```

### Jogo muito lento
- Feche outros programas
- Ou em `config.py`, mude:
  ```python
  FPS = 30  # Em vez de 60
  ```

### Sem som
É normal! O jogo cria a pasta `assets/audio` automaticamente.
Os sons são opcionais.

---

## 📊 Progresso do Jogo

| Elemento | Quantidade |
|----------|-----------|
| Cômodos | 6 |
| Pistas | 9 |
| Esconderijos | 8 |
| Finais | 2 |
| Níveis de Dificuldade | 4 |

---

## 🎓 Aprender Programação

Este projeto usa:
- **Orientação a Objetos (OOP)**
- **Máquina de Estados**
- **Padrões de Design**
- **Gerenciamento de Recursos**
- **Física Simples**

Ótimo para aprender **Python avançado**!

---

## 🚀 Próximos Passos

Após jogar, você pode:

1. **Explorar o Código**
   - Abra `clara_game_enhanced.py`
   - Leia os comentários
   - Entenda a estrutura

2. **Fazer Modificações**
   - Mudar cores em `config.py`
   - Adicionar mais pistas em `_setup_expanded_clues()`
   - Criar novos cômodos em `_create_enhanced_rooms()`

3. **Aprender Mais**
   - Leia `README_MELHORIAS.md` para detalhes técnicos
   - Estude `graphics_engine.py` para efeitos
   - Veja `cinematics.py` para cinemáticas

---

## 💡 Dicas de Jogo

1. **Explore tudo** antes da perseguição começar
2. **Leia as pistas** com atenção - elas revelam a história
3. **Encontre esconderijos** bons - cada cômodo tem vários
4. **O medo aumenta** quanto mais tempo não se esconde
5. **A escolha final importa** - ambos os finais são válidos

---

## 🎬 Versão do Jogo

- **Versão Atual:** 2.0 (Melhorada)
- **Linguagem:** Python 3.8+
- **Framework:** Pygame 2.5.2
- **Compatibilidade:** Windows, Mac, Linux

---

## 📝 Notas Finais

- Jogo foi criado como projeto educacional
- Aborda tema sensível (abuso infantil) com cuidado
- Sem violência gráfica - horror psicológico puro
- Recursos disponíveis no final

---

**Bom jogo! 🎮✨**

Qualquer dúvida, veja os outros arquivos `.md` para documentação completa.
