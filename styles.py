def build_stylesheet(t: dict) -> str:
    a   = t["accent"]
    a2  = t["accent2"]
    bg  = t["bg"]
    sb  = t["sidebar"]
    tx  = t["text"]
    dim = t["dim"]
    bdr = t["border"]
    cbg = t["chat_bg"]
    tbg = t["term_bg"]
    ttx = t["term_text"]
    err = t.get("error",   "#ef4444")
    wrn = t.get("warning", "#f59e0b")
    suc = t.get("success", a)
    umsg= t.get("user_msg", cbg)
    amsg= t.get("ai_msg",   bg)

    return f"""
/* ═══════════════════════════════════════════════════════════════════════════
   ARIA — Void Intelligence Design System
   ═══════════════════════════════════════════════════════════════════════════ */

/* ── Reset & Base ─────────────────────────────────────────────────────────── */
* {{
    outline: none;
}}
QMainWindow, QDialog {{
    background: {bg};
}}
QWidget {{
    background: transparent;
    color: {tx};
    font-family: 'Segoe UI Variable', 'Segoe UI', 'SF Pro Text', sans-serif;
    font-size: 9.5pt;
    selection-background-color: {a}30;
    selection-color: {tx};
}}
QFrame {{
    background: transparent;
    border: none;
}}

/* ── Title Bar ────────────────────────────────────────────────────────────── */
#TitleBar {{
    background: {sb};
    border-bottom: 1px solid {bdr};
}}
#TitleLabel {{
    color: {tx};
    font-size: 12pt;
    font-weight: 700;
    letter-spacing: 5px;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif;
}}
#TitleSubtitle {{
    color: {dim};
    font-size: 8pt;
    letter-spacing: 1.5px;
    font-family: 'Cascadia Code', 'Consolas', monospace;
}}
#TitleBtn {{
    background: transparent;
    color: {dim};
    border: none;
    font-size: 12pt;
    font-weight: 300;
    padding: 0;
}}
#TitleBtn:hover {{
    background: rgba(255,255,255,0.07);
    color: {tx};
}}
#TitleBtn:pressed {{
    background: rgba(255,255,255,0.04);
}}
#TitleBtnClose {{
    background: transparent;
    color: {dim};
    border: none;
    font-size: 11pt;
    padding: 0;
}}
#TitleBtnClose:hover {{
    background: {err}cc;
    color: #ffffff;
}}
#TitleBtnClose:pressed {{
    background: {err};
}}
#TitleAccentLine {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0   {a},
        stop:0.4 {a2},
        stop:1   transparent
    );
    border: none;
    max-height: 1px;
    min-height: 1px;
}}

/* ── Sidebar ──────────────────────────────────────────────────────────────── */
#Sidebar {{
    background: {sb};
    border-right: 1px solid {bdr};
    min-width: 210px;
    max-width: 210px;
}}
#SidebarLogoArea {{
    background: transparent;
    border-bottom: 1px solid {bdr};
    padding: 0;
}}
#SidebarLogo {{
    color: {tx};
    font-size: 18pt;
    font-weight: 800;
    letter-spacing: 6px;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif;
    padding: 18px 20px 6px 20px;
    background: transparent;
}}
#SidebarTagline {{
    color: {dim};
    font-size: 7pt;
    letter-spacing: 2.5px;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    padding: 0 20px 14px 22px;
    background: transparent;
}}

/* Nav buttons */
#NavBtn {{
    background: transparent;
    color: {dim};
    border: none;
    border-left: 3px solid transparent;
    border-radius: 0;
    padding: 11px 18px 11px 20px;
    text-align: left;
    font-size: 9.5pt;
    font-weight: 500;
    letter-spacing: 0.3px;
    margin: 1px 0;
}}
#NavBtn:hover {{
    background: rgba(255,255,255,0.04);
    color: {tx};
    border-left: 3px solid {bdr};
}}
#NavBtnActive {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 {a}18,
        stop:1 transparent
    );
    color: {a};
    border: none;
    border-left: 3px solid {a};
    border-radius: 0;
    padding: 11px 18px 11px 20px;
    text-align: left;
    font-size: 9.5pt;
    font-weight: 600;
    letter-spacing: 0.3px;
    margin: 1px 0;
}}
#NavBtnActive:hover {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 {a}25,
        stop:1 transparent
    );
}}

/* Sidebar sections */
#SidebarSection {{
    background: transparent;
    color: {dim};
    font-size: 7pt;
    letter-spacing: 2px;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    padding: 10px 20px 4px 20px;
    text-transform: uppercase;
    border: none;
}}
#SysInfo {{
    color: {dim};
    font-size: 8pt;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    padding: 2px 20px;
    background: transparent;
    letter-spacing: 0.3px;
    line-height: 1.7;
}}

/* Toggle & Mic buttons */
#ToggleBtn {{
    background: transparent;
    color: {dim};
    border: none;
    border-radius: 0;
    padding: 9px 18px 9px 20px;
    text-align: left;
    font-size: 9pt;
    letter-spacing: 0.3px;
    border-left: 3px solid transparent;
    margin: 1px 0;
}}
#ToggleBtn:hover {{
    background: rgba(255,255,255,0.04);
    color: {tx};
}}
#ToggleBtn:checked {{
    color: {a};
    background: {a}0f;
    border-left: 3px solid {a}60;
}}
#MicBtn {{
    background: transparent;
    color: {dim};
    border: 1px solid {bdr};
    border-radius: 8px;
    padding: 9px 14px;
    margin: 4px 12px;
    text-align: center;
    font-size: 9pt;
    letter-spacing: 0.3px;
}}
#MicBtn:hover {{
    background: {a}15;
    color: {a};
    border-color: {a}50;
}}
#MicBtnActive {{
    background: {err}20;
    color: {err};
    border: 1px solid {err}60;
    border-radius: 8px;
    padding: 9px 14px;
    margin: 4px 12px;
    text-align: center;
    font-size: 9pt;
}}

/* Theme combo */
#ThemeCombo {{
    background: {cbg};
    color: {tx};
    border: 1px solid {bdr};
    border-radius: 7px;
    padding: 6px 10px;
    font-size: 9pt;
    margin: 4px 12px;
    selection-background-color: {a}30;
}}
#ThemeCombo:hover {{
    border-color: {a}50;
}}
#ThemeCombo::drop-down {{
    border: none;
    width: 20px;
}}
#ThemeCombo QAbstractItemView {{
    background: {cbg};
    border: 1px solid {bdr};
    border-radius: 7px;
    color: {tx};
    selection-background-color: {a}25;
    padding: 4px;
    outline: none;
}}

/* ── Chat Area ────────────────────────────────────────────────────────────── */
#ChatArea {{
    background: {bg};
    border: none;
}}
QScrollArea#ChatArea > QWidget > QWidget {{
    background: {bg};
}}

/* Message roles */
#MessageRole {{
    color: {dim};
    font-size: 7.5pt;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    letter-spacing: 1px;
    padding: 0 2px 3px 2px;
    background: transparent;
    text-transform: uppercase;
}}

/* Chat bubbles */
#UserBubble {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 {umsg},
        stop:1 {umsg}cc
    );
    color: {tx};
    border: 1px solid {a}30;
    border-radius: 14px;
    border-bottom-right-radius: 4px;
    padding: 10px 14px;
    font-size: 9.5pt;
    line-height: 1.65;
}}
#AiBubble {{
    background: {amsg};
    color: {tx};
    border: 1px solid {bdr};
    border-left: 2px solid {a}60;
    border-radius: 14px;
    border-bottom-left-radius: 4px;
    padding: 10px 14px;
    font-size: 9.5pt;
    line-height: 1.65;
}}

/* Streaming display */
#ChatDisplay {{
    background: {amsg};
    color: {tx};
    border: 1px solid {bdr};
    border-left: 2px solid {a}50;
    border-radius: 12px;
    padding: 12px 16px;
    font-size: 9.5pt;
    line-height: 1.65;
    selection-background-color: {a}25;
}}

/* Typing indicator */
#TypingIndicator {{
    color: {a};
    font-size: 8pt;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    letter-spacing: 0.5px;
    padding: 6px 20px;
    background: transparent;
}}

/* STT status */
#STTStatus {{
    color: {err};
    font-size: 8pt;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    letter-spacing: 0.8px;
    padding: 4px 20px;
    background: transparent;
}}

/* Suggestion pills */
#SuggestionBtn {{
    background: {cbg};
    color: {dim};
    border: 1px solid {bdr};
    border-radius: 20px;
    padding: 5px 14px;
    font-size: 8.5pt;
    letter-spacing: 0.2px;
}}
#SuggestionBtn:hover {{
    background: {a}15;
    color: {a};
    border-color: {a}60;
}}
#SuggestionBtn:pressed {{
    background: {a}25;
}}

/* Input area */
#InputArea {{
    background: {cbg};
    border-top: 1px solid {bdr};
    padding: 0;
}}
#ChatInput {{
    background: {bg};
    color: {tx};
    border: 1px solid {bdr};
    border-radius: 10px;
    padding: 10px 14px;
    font-size: 9.5pt;
    selection-background-color: {a}25;
}}
#ChatInput:focus {{
    border-color: {a}60;
    background: {cbg};
}}
#ChatInput::placeholder {{
    color: {dim};
}}
#SendBtn {{
    background: {a};
    color: {bg};
    border: none;
    border-radius: 10px;
    padding: 10px 0;
    font-weight: 700;
    font-size: 9pt;
    letter-spacing: 0.5px;
    min-width: 72px;
}}
#SendBtn:hover {{
    background: {a2};
    color: #ffffff;
}}
#SendBtn:pressed {{
    background: {a}bb;
}}

/* ── Terminal ─────────────────────────────────────────────────────────────── */
#SectionHeader {{
    color: {tx};
    font-size: 12pt;
    font-weight: 700;
    letter-spacing: 0.5px;
    font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif;
    background: transparent;
    padding-bottom: 2px;
}}
#TerminalOutput {{
    background: {tbg};
    color: {ttx};
    border: 1px solid {bdr};
    border-radius: 12px;
    padding: 16px 20px;
    font-size: 9.5pt;
    font-family: 'Cascadia Code', 'Consolas', 'Courier New', monospace;
    selection-background-color: {a}25;
    line-height: 1.6;
}}
#TerminalPrompt {{
    color: {a};
    font-family: 'Cascadia Code', 'Consolas', monospace;
    font-size: 9.5pt;
    font-weight: 600;
    background: transparent;
    padding: 0 6px;
}}
#TerminalInput {{
    background: {tbg};
    color: {ttx};
    border: 1px solid {bdr};
    border-radius: 8px;
    padding: 9px 14px;
    font-size: 9.5pt;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    selection-background-color: {a}25;
}}
#TerminalInput:focus {{
    border-color: {a}50;
}}

/* ── Timeline ─────────────────────────────────────────────────────────────── */
#TimelineEntry {{
    background: {cbg};
    border: 1px solid {bdr};
    border-radius: 8px;
    margin: 2px 0;
}}
#TimelineEntry:hover {{
    border-color: {a}40;
    background: {a}08;
}}
#TimelineTime {{
    color: {dim};
    font-size: 7.5pt;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    letter-spacing: 0.5px;
    background: transparent;
}}
#TimelineText {{
    color: {tx};
    font-size: 8.5pt;
    background: transparent;
    line-height: 1.5;
}}

/* ── Warnings ─────────────────────────────────────────────────────────────── */
#WarningEntryError {{
    background: {err}0c;
    border: 1px solid {err}35;
    border-left: 3px solid {err};
    border-radius: 8px;
    margin: 2px 0;
}}
#WarningEntryWarning {{
    background: {wrn}0c;
    border: 1px solid {wrn}35;
    border-left: 3px solid {wrn};
    border-radius: 8px;
    margin: 2px 0;
}}
#WarningEntryInfo {{
    background: {a}08;
    border: 1px solid {a}25;
    border-left: 3px solid {a}80;
    border-radius: 8px;
    margin: 2px 0;
}}
#ClearWarningsBtn {{
    background: transparent;
    color: {dim};
    border: 1px solid {bdr};
    border-radius: 8px;
    padding: 7px 16px;
    font-size: 9pt;
}}
#ClearWarningsBtn:hover {{
    background: {err}15;
    color: {err};
    border-color: {err}50;
}}

/* ── Self-Mod Page ────────────────────────────────────────────────────────── */
#ProposalCard {{
    background: {cbg};
    border: 1px solid {bdr};
    border-top: 2px solid {a}60;
    border-radius: 12px;
    margin: 4px 0;
}}
#ProposalTitle {{
    color: {tx};
    font-size: 10pt;
    font-weight: 600;
    background: transparent;
    letter-spacing: 0.2px;
}}
#ProposalText {{
    color: {tx};
    font-size: 9pt;
    line-height: 1.65;
    background: transparent;
}}
#ProposalMeta {{
    color: {dim};
    font-size: 8.5pt;
    background: transparent;
    line-height: 1.5;
}}
#ApproveBtn {{
    background: {suc}18;
    color: {suc};
    border: 1px solid {suc}55;
    border-radius: 8px;
    padding: 7px 18px;
    font-weight: 600;
    font-size: 9pt;
    letter-spacing: 0.3px;
}}
#ApproveBtn:hover {{
    background: {suc}30;
    border-color: {suc}90;
}}
#ApproveBtn:pressed {{
    background: {suc}20;
}}
#RejectBtn {{
    background: {err}10;
    color: {err};
    border: 1px solid {err}40;
    border-radius: 8px;
    padding: 7px 18px;
    font-size: 9pt;
    letter-spacing: 0.3px;
}}
#RejectBtn:hover {{
    background: {err}25;
    border-color: {err}70;
}}
#RollbackBtn {{
    background: transparent;
    color: {dim};
    border: 1px solid {bdr};
    border-radius: 7px;
    padding: 5px 12px;
    font-size: 8pt;
    letter-spacing: 0.3px;
}}
#RollbackBtn:hover {{
    color: {wrn};
    border-color: {wrn}60;
    background: {wrn}10;
}}
#LedgerEntry {{
    background: {cbg};
    border: 1px solid {bdr};
    border-radius: 8px;
    margin: 2px 0;
}}
#LedgerEntry:hover {{
    border-color: {a}30;
}}
#LedgerEntryRolledBack {{
    background: transparent;
    border: 1px solid {bdr}88;
    border-radius: 8px;
    margin: 2px 0;
    color: {dim};
}}
#AnalyzeBtn {{
    background: {a}18;
    color: {a};
    border: 1px solid {a}55;
    border-radius: 9px;
    padding: 8px 20px;
    font-weight: 600;
    font-size: 9pt;
    letter-spacing: 0.3px;
}}
#AnalyzeBtn:hover {{
    background: {a}30;
    border-color: {a}99;
}}

/* ── Status Bar ───────────────────────────────────────────────────────────── */
#StatusBar {{
    background: {sb};
    border-top: 1px solid {bdr};
    min-height: 22px;
    max-height: 22px;
}}
#StatusDot {{
    color: {suc};
    font-size: 8pt;
    background: transparent;
}}
#StatusDotOffline {{
    color: {err};
    font-size: 8pt;
    background: transparent;
}}
#StatusLabel {{
    color: {dim};
    font-size: 8pt;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    background: transparent;
    letter-spacing: 0.3px;
}}
#LLMLabel {{
    color: {a};
    font-size: 8pt;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    background: transparent;
    letter-spacing: 0.3px;
}}

/* ── Tabs ─────────────────────────────────────────────────────────────────── */
QTabWidget::pane {{
    border: 1px solid {bdr};
    border-radius: 10px;
    background: {cbg};
    top: -1px;
}}
QTabBar {{
    background: transparent;
}}
QTabBar::tab {{
    background: transparent;
    color: {dim};
    border: none;
    border-bottom: 2px solid transparent;
    padding: 9px 20px;
    font-size: 9pt;
    margin: 0 1px;
    letter-spacing: 0.3px;
}}
QTabBar::tab:selected {{
    color: {a};
    border-bottom: 2px solid {a};
    font-weight: 600;
}}
QTabBar::tab:hover {{
    color: {tx};
    background: {a}0a;
}}

/* ── Scrollbars ───────────────────────────────────────────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: 4px;
    border: none;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {bdr};
    border-radius: 2px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {a}55;
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0;
    background: transparent;
}}
QScrollBar:horizontal {{
    height: 0;
    background: transparent;
}}

/* ── General Buttons ──────────────────────────────────────────────────────── */
QPushButton {{
    background: {cbg};
    color: {tx};
    border: 1px solid {bdr};
    border-radius: 8px;
    padding: 7px 14px;
    font-size: 9pt;
    letter-spacing: 0.2px;
}}
QPushButton:hover {{
    background: rgba(255,255,255,0.05);
    border-color: {a}45;
    color: {tx};
}}
QPushButton:pressed {{
    background: rgba(255,255,255,0.02);
}}

/* ── Text / Line Edits ────────────────────────────────────────────────────── */
QLineEdit {{
    background: {cbg};
    color: {tx};
    border: 1px solid {bdr};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 9.5pt;
    selection-background-color: {a}25;
}}
QLineEdit:focus {{
    border-color: {a}60;
}}
QPlainTextEdit {{
    background: {cbg};
    color: {tx};
    border: 1px solid {bdr};
    border-radius: 10px;
    padding: 10px;
    font-size: 9.5pt;
    selection-background-color: {a}25;
}}

/* ── Tooltips ─────────────────────────────────────────────────────────────── */
QToolTip {{
    background: {cbg};
    color: {tx};
    border: 1px solid {bdr};
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 8.5pt;
}}

/* ── Labels (general) ─────────────────────────────────────────────────────── */
QLabel {{
    background: transparent;
    color: {tx};
}}
"""