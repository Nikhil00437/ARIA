"""ARIA stylesheet — Modern, minimal, dark theme.

Linear/Vercel-style: warm slate base, muted indigo accent, hairline borders,
no neon glows, no capsule rounding. The stylesheet is generated from a theme
dict so switching themes at runtime actually swaps colors.

`build_stylesheet(t)` is called once at startup and again whenever the user
changes theme. Every literal hex in this file is replaced by a `t["key"]`
lookup. Missing keys fall back to safe defaults.
"""

from __future__ import annotations


# Safe defaults so a partial theme still renders cleanly.
_DEFAULTS = {
    "bg":            "#0E0F13",
    "bg2":           "#16181D",
    "bg3":           "#1D1F26",
    "accent":        "#8B8CF7",
    "accent2":       "#6366F1",
    "accent_text":   "#0E0F13",
    "text":          "#E6E8EE",
    "text2":         "#9CA3AF",
    "dim":           "#525866",
    "border":        "#262932",
    "row_hover":     "#1D1F26",
    "code_bg":       "#16181D",
    "sidebar":       "#0B0C10",
    "term_text":     "#E6E8EE",
    "warning":       "#F59E0B",
    "error":         "#EF4444",
    "success":       "#10B981",
    "kind_thought":     "#525866",
    "kind_plan":        "#8B8CF7",
    "kind_action":      "#F59E0B",
    "kind_observation": "#10B981",
}


def _t(t: dict, key: str) -> str:
    """Safe theme lookup with default fallback."""
    v = t.get(key) if t else None
    if v is None or v == "":
        return _DEFAULTS[key]
    return v


def build_stylesheet(t: dict) -> str:
    """Return the global QSS stylesheet for theme ``t``.

    All colors come from ``t``; every selector below is theme-switchable.
    """
    bg          = _t(t, "bg")
    bg2         = _t(t, "bg2")
    bg3         = _t(t, "bg3")
    accent      = _t(t, "accent")
    accent2     = _t(t, "accent2")
    accent_text = _t(t, "accent_text")
    text        = _t(t, "text")
    text2       = _t(t, "text2")
    dim         = _t(t, "dim")
    border      = _t(t, "border")
    row_hover   = _t(t, "row_hover")
    sidebar     = _t(t, "sidebar")
    term_text   = _t(t, "term_text")
    warning     = _t(t, "warning")
    error       = _t(t, "error")
    success     = _t(t, "success")
    kind_thought     = _t(t, "kind_thought")
    kind_plan        = _t(t, "kind_plan")
    kind_action      = _t(t, "kind_action")
    kind_observation = _t(t, "kind_observation")

    return f"""
    /* ═══════════════════════════════════════════════════════════════
       ARIA — MODERN MINIMAL DARK THEME
       ═══════════════════════════════════════════════════════════════ */

    /* ── Base ──────────────────────────────────────────────────── */
    QMainWindow {{
        background: transparent;
    }}
    QWidget {{
        background: transparent;
        color: {text};
        font-family: 'Segoe UI Variable Text', 'Segoe UI', -apple-system, sans-serif;
        font-size: 10pt;
    }}
    QDialog {{
        background: {bg};
        border: 1px solid {border};
        border-radius: 6px;
    }}
    QStackedWidget {{
        background: transparent;
        border: none;
    }}

    /* ── Top chrome ────────────────────────────────────────────── */
    QWidget#TitleBar {{
        background: {sidebar};
        border: none;
        border-bottom: 1px solid {border};
    }}
    QWidget#Sidebar {{
        background: {sidebar};
        border: none;
        border-bottom: 1px solid {border};
    }}
    QWidget#StatusBar {{
        background: transparent;
        border: none;
        border-top: 1px solid {border};
    }}

    /* All pages — flat against the window gradient */
    QWidget#ChatPage, QWidget#TerminalPage, QWidget#TimelinePage,
    QWidget#WarningsPage, QWidget#SelfModPage, QWidget#PatternsPage,
    QWidget#AgentTaskPage {{
        background: transparent;
    }}

    /* ── Surfaces / Cards ──────────────────────────────────────── */
    QWidget#GlassPanel {{
        background: {bg2};
        border: 1px solid {border};
        border-radius: 6px;
    }}
    QWidget#GlassPanel:hover {{
        background: {row_hover};
    }}
    QWidget#GlassPanelHeader {{
        background: transparent;
        border: none;
        border-bottom: 1px solid {border};
        border-radius: 6px 6px 0 0;
    }}
    QLabel#GlassPanelTitle {{
        color: {text2};
        text-transform: uppercase;
        letter-spacing: 1px;
        font-size: 7.5pt;
        font-weight: 700;
    }}

    QFrame {{
        background: transparent;
        border: none;
    }}
    QWidget#Card {{
        background: {bg2};
        border: 1px solid {border};
        border-radius: 6px;
    }}
    QFrame[frameShape="4"], QFrame[frameShape="5"] {{
        background: {border};
        border: none;
    }}

    /* ── Labels ─────────────────────────────────────────────────── */
    QLabel {{
        color: {text};
        background: transparent;
        border: none;
    }}

    QLabel#TitleLogo {{
        color: {accent};
        font-size: 13pt;
        font-weight: 800;
        font-family: 'Cascadia Code', 'Consolas', monospace;
        letter-spacing: 1px;
    }}
    QLabel#TitleLabel {{
        color: {text};
        font-size: 9pt;
        font-weight: 700;
        letter-spacing: 2px;
        font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif;
    }}
    QLabel#TitleSubtitle {{
        color: {text2};
        font-size: 8pt;
    }}
    QLabel#RailLogo {{
        color: {accent};
        font-size: 16px;
        font-weight: 800;
    }}
    QLabel#SectionHeader {{
        color: {text};
        font-size: 11pt;
        font-weight: 700;
        font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif;
        letter-spacing: 0.5px;
    }}

    /* Chat bubbles — borderless, text only */
    QLabel#AiBubble {{
        background: transparent;
        border: none;
        color: {text};
        padding: 0px;
        font-size: 10pt;
        line-height: 1.5;
    }}
    QLabel#UserBubble {{
        background: transparent;
        border: none;
        color: {text};
        padding: 0px;
        font-size: 10pt;
        line-height: 1.5;
    }}

    QWidget#ChatArea {{
        background: transparent;
        border: none;
    }}
    QLabel#MessageRole {{
        color: {text2};
        font-size: 8pt;
        font-weight: 700;
        letter-spacing: 0.5px;
    }}
    QLabel#TypingIndicator {{
        color: {text2};
        font-size: 9pt;
        padding: 4px 0;
    }}
    QLabel#Avatar {{
        background: {bg2};
        color: {accent};
        border: 1px solid {border};
        border-radius: 14px;
        font-size: 10pt;
        font-weight: 700;
        qproperty-alignment: AlignCenter;
    }}
    QLabel#AvatarUser {{
        background: {bg2};
        color: {text};
        border: 1px solid {border};
        border-radius: 14px;
        font-size: 10pt;
        font-weight: 700;
        qproperty-alignment: AlignCenter;
    }}

    QPushButton#ReactionBtn {{
        background: transparent;
        color: {text2};
        border: 1px solid {border};
        border-radius: 4px;
        padding: 2px 6px;
        font-size: 9pt;
    }}
    QPushButton#ReactionBtn:hover {{
        background: {row_hover};
        color: {text};
        border-color: {accent};
    }}
    QPushButton#ReactionBtn:checked {{
        background: {accent};
        color: {accent_text};
        border-color: {accent};
    }}

    QLabel#LoadingSpinner {{
        color: {accent};
        font-size: 12pt;
    }}
    QLabel#STTStatus {{
        color: {error};
        font-size: 8pt;
        padding: 4px 0;
    }}

    /* ── Status bar ─────────────────────────────────────────────── */
    QLabel#StatusDot {{
        color: {success};
        font-size: 8pt;
    }}
    QLabel#StatusDotOffline {{
        color: {error};
        font-size: 8pt;
    }}
    QLabel#StatusLabel {{
        color: {text2};
        font-size: 8pt;
    }}
    QLabel#LLMLabel {{
        color: {dim};
        font-size: 7.5pt;
        font-family: 'Cascadia Code', 'Consolas', monospace;
    }}
    QLabel#NotifDot {{
        color: {error};
        font-size: 8pt;
        font-weight: 800;
    }}

    /* ── Sidebar stats ──────────────────────────────────────────── */
    QLabel#SidebarStatLabel {{
        color: {text2};
        font-family: 'Cascadia Code', 'Consolas', monospace;
        font-size: 7pt;
        font-weight: 700;
        letter-spacing: 1px;
    }}
    QFrame#SidebarStatBar {{
        background: {bg3};
        border: none;
        border-radius: 1px;
    }}
    QFrame#SidebarDivider {{
        background: {border};
        border: none;
    }}
    QFrame#SidebarAccent {{
        background: {accent};
        border: none;
    }}
    QFrame#RailStatFill_CPU {{
        background: {accent};
        border: none;
        border-radius: 1px;
    }}
    QFrame#RailStatFill_RAM {{
        background: {accent2};
        border: none;
        border-radius: 1px;
    }}
    QFrame#RailStatBar {{
        background: {bg3};
        border: none;
        border-radius: 1px;
    }}

    /* ── Timeline / Warning entries ────────────────────────────── */
    QLabel#TimelineTime {{
        color: {dim};
        font-size: 8pt;
        font-family: 'Cascadia Code', 'Consolas', monospace;
    }}
    QLabel#TimelineText {{
        color: {text};
        font-size: 9.5pt;
    }}
    QLabel#TimelineIcon {{
        color: {text2};
        font-size: 11pt;
        background: transparent;
    }}
    QWidget#TimelineEntry {{
        background: transparent;
        border: none;
        border-bottom: 1px solid {border};
    }}
    QWidget#TimelineEntry:hover {{
        background: {row_hover};
    }}
    QWidget#WarningEntryError {{
        background: transparent;
        border: 1px solid {border};
        border-left: 3px solid {error};
        border-radius: 4px;
    }}
    QWidget#WarningEntryWarning {{
        background: transparent;
        border: 1px solid {border};
        border-left: 3px solid {warning};
        border-radius: 4px;
    }}
    QWidget#WarningEntryInfo {{
        background: transparent;
        border: 1px solid {border};
        border-left: 3px solid {accent};
        border-radius: 4px;
    }}
    QLabel#WarningIcon {{
        color: {text2};
        font-size: 10pt;
        background: transparent;
    }}
    QLabel#WarningText {{
        color: {text};
        font-size: 9pt;
    }}

    /* ── Pattern cards ──────────────────────────────────────────── */
    QLabel#PatternCardName {{
        color: {text};
        font-size: 10pt;
        font-weight: 700;
    }}
    QLabel#PatternCardSlug {{
        color: {text2};
        font-size: 8pt;
        font-family: 'Cascadia Code', 'Consolas', monospace;
    }}
    QLabel#PatternCardPreview {{
        color: {text2};
        font-size: 9pt;
    }}
    QLabel#PatternCount {{
        color: {dim};
        font-size: 8pt;
    }}
    QLabel#PatternStatus {{
        color: {accent};
        font-size: 8pt;
        font-weight: 700;
    }}

    /* ── Proposal / Ledger ──────────────────────────────────────── */
    QLabel#ProposalTitle {{
        color: {text};
        font-size: 10pt;
        font-weight: 700;
    }}
    QLabel#ProposalText {{
        color: {text};
        font-size: 9.5pt;
    }}
    QLabel#ProposalMeta {{
        color: {text2};
        font-size: 8pt;
    }}
    QLabel#ProposalValue {{
        background: {bg3};
        color: {success};
        border: 1px solid {border};
        border-radius: 4px;
        padding: 2px 8px;
        font-family: 'Cascadia Code', 'Consolas', monospace;
        font-size: 8.5pt;
        font-weight: 700;
    }}
    QWidget#ProposalCard {{
        background: {bg2};
        border: 1px solid {border};
        border-radius: 6px;
    }}
    QWidget#ProposalCard:hover {{
        border-color: {accent};
    }}
    QWidget#LedgerEntry {{
        background: transparent;
        border-bottom: 1px solid {border};
    }}
    QWidget#LedgerEntry:hover {{
        background: {row_hover};
    }}
    QWidget#LedgerEntryRolledBack {{
        background: transparent;
        border: 1px dashed {border};
        border-radius: 4px;
    }}
    QWidget#LedgerEntryRolledBack:hover {{
        border-color: {warning};
    }}

    /* ── Pattern browser ────────────────────────────────────────── */
    QWidget#PatternBrowser {{
        background: transparent;
        border: none;
        border-right: 1px solid {border};
    }}
    QWidget#PatternCard {{
        background: transparent;
        border: 1px solid transparent;
        border-radius: 6px;
    }}
    QWidget#PatternCard:hover {{
        background: {row_hover};
    }}
    QWidget#PatternCardActive {{
        background: {row_hover};
        border: 1px solid {accent};
        border-radius: 6px;
    }}

    /* ── Sidebar nav tabs (active state uses accent + underline) ── */
    QPushButton#RailBtn {{
        background: transparent;
        color: {text2};
        border: none;
        font-size: 9pt;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        padding: 8px 12px;
        margin: 0px 2px;
        border-radius: 4px;
    }}
    QPushButton#RailBtn:hover {{
        color: {text};
        background: {row_hover};
    }}
    QPushButton#RailBtnActive {{
        background: transparent;
        color: {text};
        border: none;
        border-bottom: 2px solid {accent};
        font-size: 9pt;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        padding: 8px 12px;
        margin: 0px 2px;
        border-radius: 4px;
    }}
    QPushButton#RailBtnActive:hover {{
        color: {accent};
    }}

    /* ── Title bar buttons ──────────────────────────────────────── */
    QPushButton#TitleBtn, QPushButton#TitleBtnSettings {{
        background: transparent;
        color: {text2};
        border: none;
        font-size: 9pt;
        padding: 4px 8px;
        border-radius: 4px;
    }}
    QPushButton#TitleBtn:hover, QPushButton#TitleBtnSettings:hover {{
        background: {row_hover};
        color: {text};
    }}
    QPushButton#TitleBtnClose {{
        background: transparent;
        color: {text2};
        border: none;
        font-size: 9pt;
        padding: 4px 8px;
        border-radius: 4px;
    }}
    QPushButton#TitleBtnClose:hover {{
        background: {error};
        color: #ffffff;
    }}

    /* ── Default PushButton (subdued) ───────────────────────────── */
    QPushButton {{
        background: {bg2};
        color: {text};
        border: 1px solid {border};
        border-radius: 4px;
        padding: 5px 12px;
        font-size: 9pt;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background: {row_hover};
        border-color: {accent};
    }}
    QPushButton:pressed {{
        background: {bg3};
        border-color: {accent};
        color: {accent};
    }}
    QPushButton:disabled {{
        background: {bg2};
        color: {dim};
        border-color: {border};
    }}

    /* ── Chat input area ────────────────────────────────────────── */
    QWidget#InputArea {{
        background: {bg2};
        border: 1px solid {border};
        border-radius: 6px;
    }}
    QPlainTextEdit#ChatInput {{
        background: transparent;
        border: none;
        color: {text};
        padding: 4px;
        font-size: 10pt;
    }}
    QPushButton#SendBtn {{
        background: {accent};
        color: {accent_text};
        border: none;
        border-radius: 4px;
        font-weight: 700;
        padding: 6px 14px;
    }}
    QPushButton#SendBtn:hover {{
        background: {accent2};
    }}
    QPushButton#SendBtn:pressed {{
        background: {accent2};
    }}
    QPushButton#SendBtn:disabled {{
        background: {bg3};
        color: {dim};
    }}

    /* ── Suggestion chips ───────────────────────────────────────── */
    QPushButton#SuggestionBtn {{
        background: {bg2};
        color: {text2};
        border: 1px solid {border};
        border-radius: 4px;
        padding: 4px 10px;
        font-size: 8pt;
    }}
    QPushButton#SuggestionBtn:hover {{
        background: {row_hover};
        color: {text};
        border-color: {accent};
    }}
    QPushButton#SuggestionBtn:pressed {{
        background: {accent};
        color: {accent_text};
        border-color: {accent};
    }}

    /* ── Quick action buttons ───────────────────────────────────── */
    QPushButton#QuickBtn {{
        background: {bg2};
        color: {text2};
        border: 1px solid {border};
        border-radius: 4px;
        font-size: 8.5pt;
        padding: 8px 4px;
        text-align: center;
    }}
    QPushButton#QuickBtn:hover {{
        background: {row_hover};
        color: {text};
        border-color: {accent};
    }}
    QPushButton#QuickBtn:pressed {{
        background: {accent};
        color: {accent_text};
    }}

    /* ── Approval / action buttons ──────────────────────────────── */
    QPushButton#ApproveBtn {{
        background: {accent};
        color: {accent_text};
        border: 1px solid {accent};
        border-radius: 4px;
        padding: 6px 14px;
        font-weight: 700;
    }}
    QPushButton#ApproveBtn:hover {{
        background: {accent2};
        border-color: {accent2};
    }}
    QPushButton#RejectBtn {{
        background: {bg2};
        color: {error};
        border: 1px solid {border};
        border-radius: 4px;
        padding: 6px 14px;
    }}
    QPushButton#RejectBtn:hover {{
        background: {error};
        color: #ffffff;
        border-color: {error};
    }}
    QPushButton#AnalyzeBtn {{
        background: {bg2};
        color: {accent};
        border: 1px solid {border};
        border-radius: 4px;
        padding: 6px 14px;
        font-weight: 700;
    }}
    QPushButton#AnalyzeBtn:hover {{
        background: {accent};
        color: {accent_text};
        border-color: {accent};
    }}
    QPushButton#RollbackBtn {{
        background: {bg2};
        color: {text2};
        border: 1px solid {border};
        border-radius: 4px;
        padding: 4px 8px;
    }}
    QPushButton#RollbackBtn:hover {{
        color: {text};
        border-color: {accent};
    }}
    QPushButton#ClearWarningsBtn {{
        background: {bg2};
        color: {text2};
        border: 1px solid {border};
        border-radius: 4px;
        padding: 6px 14px;
    }}
    QPushButton#ClearWarningsBtn:hover {{
        color: {text};
        border-color: {accent};
    }}

    /* ── Pattern page buttons ───────────────────────────────────── */
    QPushButton#PatternRunBtn {{
        background: {accent};
        color: {accent_text};
        border: none;
        border-radius: 4px;
        padding: 8px 0;
        font-weight: 700;
        text-transform: uppercase;
    }}
    QPushButton#PatternRunBtn:hover {{
        background: {accent2};
    }}
    QPushButton#PatternRunBtn:disabled {{
        background: {bg3};
        color: {dim};
    }}
    QPushButton#PatternActionBtn {{
        background: {bg2};
        color: {text2};
        border: 1px solid {border};
        border-radius: 4px;
        padding: 4px 10px;
    }}
    QPushButton#PatternActionBtn:hover {{
        color: {text};
        border-color: {accent};
    }}
    QPushButton#PatternToggleBtn {{
        background: transparent;
        color: {text2};
        border: none;
        text-align: left;
        font-size: 8pt;
        padding: 2px 0;
    }}
    QPushButton#PatternToggleBtn:hover {{
        color: {text};
    }}
    QPushButton#TerminalRunBtn {{
        background: {accent};
        color: {accent_text};
        border: none;
        border-radius: 4px;
        padding: 6px 14px;
        font-weight: 700;
    }}
    QPushButton#TerminalRunBtn:hover {{
        background: {accent2};
    }}
    QPushButton#TerminalRunBtn:disabled {{
        background: {bg3};
        color: {dim};
    }}

    /* ── Inputs ─────────────────────────────────────────────────── */
    QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {{
        background: {bg3};
        border: 1px solid {border};
        border-radius: 4px;
        color: {text};
        padding: 6px 8px;
        selection-background-color: {accent};
        selection-color: {accent_text};
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{
        border-color: {accent};
    }}
    QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover, QComboBox:hover {{
        border-color: {text2};
    }}
    QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled, QComboBox:disabled {{
        color: {dim};
        background: {bg2};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 16px;
    }}
    QComboBox QAbstractItemView {{
        background: {bg2};
        border: 1px solid {border};
        color: {text};
        selection-background-color: {row_hover};
        selection-color: {text};
        outline: 0;
    }}

    /* Terminal */
    QPlainTextEdit#TerminalOutput {{
        background: {bg};
        color: {term_text};
        border: 1px solid {border};
        border-radius: 4px;
        padding: 12px;
        font-size: 9.5pt;
        font-family: 'Cascadia Code', 'JetBrains Mono', 'Consolas', monospace;
    }}
    QLineEdit#TerminalInput {{
        background: {bg3};
        border: 1px solid {border};
        border-radius: 4px;
        padding: 8px 10px;
        font-family: 'Cascadia Code', 'Consolas', monospace;
    }}
    QLineEdit#TerminalInput:focus {{
        border-color: {accent};
    }}
    QLabel#TerminalPrompt {{
        color: {accent};
        font-family: 'Cascadia Code', monospace;
        font-size: 10pt;
        font-weight: 700;
    }}

    /* Pattern inputs */
    QLineEdit#PatternSearch, QLineEdit#PatternInput {{
        background: {bg3};
        border: 1px solid {border};
        border-radius: 4px;
        padding: 6px 10px;
    }}
    QLineEdit#PatternSearch:focus, QLineEdit#PatternInput:focus {{
        border-color: {accent};
    }}
    QTextEdit#PatternOutput {{
        background: {bg};
        color: {text};
        border: 1px solid {border};
        border-radius: 4px;
        padding: 12px;
    }}
    QTextEdit#PatternPromptPreview {{
        background: {bg2};
        color: {text2};
        border: 1px solid {border};
        border-radius: 4px;
        padding: 6px;
        font-family: 'Cascadia Code', 'Consolas', monospace;
        font-size: 8pt;
    }}

    /* ── Scrollbars (subtle) ────────────────────────────────────── */
    QScrollArea {{
        background: transparent;
        border: none;
    }}
    QScrollArea > QWidget > QWidget {{
        background: transparent;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 4px 2px 4px 0;
    }}
    QScrollBar::handle:vertical {{
        background: {border};
        min-height: 30px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {text2};
    }}
    QScrollBar::handle:vertical:pressed {{
        background: {accent};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: transparent;
    }}
    QScrollBar:horizontal {{
        height: 0px;
    }}

    /* ── Menus ──────────────────────────────────────────────────── */
    QMenuBar, QMenu {{
        background: {bg2};
        color: {text};
        border: 1px solid {border};
    }}
    QMenu::item:selected {{
        background: {row_hover};
        color: {accent};
    }}

    /* ── Tabs ───────────────────────────────────────────────────── */
    QTabWidget::pane {{
        border: 1px solid {border};
        background: transparent;
        border-radius: 4px;
        margin-top: -1px;
    }}
    QTabBar::tab {{
        background: transparent;
        color: {text2};
        border: none;
        border-bottom: 2px solid transparent;
        padding: 7px 14px;
        margin-right: 2px;
    }}
    QTabBar::tab:hover {{
        color: {text};
    }}
    QTabBar::tab:selected {{
        background: transparent;
        color: {text};
        border-bottom: 2px solid {accent};
    }}

    /* ── Tooltips ───────────────────────────────────────────────── */
    QToolTip {{
        background: {bg2};
        color: {text};
        border: 1px solid {border};
        border-radius: 4px;
        padding: 6px 10px;
        font-size: 8.5pt;
    }}

    /* ── Toasts (rounded minimal) ───────────────────────────────── */
    QWidget#Toast {{
        background: {bg2};
        border: 1px solid {border};
        border-left: 3px solid {accent};
        border-radius: 4px;
    }}
    QWidget#Toast[toastKind="success"] {{
        border-left-color: {success};
    }}
    QWidget#Toast[toastKind="warning"] {{
        border-left-color: {warning};
    }}
    QWidget#Toast[toastKind="error"] {{
        border-left-color: {error};
    }}
    QWidget#Toast[toastKind="info"] {{
        border-left-color: {accent};
    }}
    QLabel#ToastLabel {{
        color: {text};
        font-size: 9pt;
    }}
    QPushButton#ToastClose {{
        background: transparent;
        color: {dim};
        border: none;
        font-size: 10pt;
        padding: 0 6px;
    }}
    QPushButton#ToastClose:hover {{
        color: {text};
    }}

    /* ── ConfidenceBadge ────────────────────────────────────────── */
    QLabel#ConfidenceBadge {{
        background: {bg3};
        color: {text2};
        border: 1px solid {border};
        border-radius: 10px;
        padding: 2px 8px;
        font-size: 8pt;
        font-weight: 700;
    }}
    QLabel#ConfidenceBadgeHigh {{
        background: {bg3};
        color: {success};
        border: 1px solid {success};
        border-radius: 10px;
        padding: 2px 8px;
        font-size: 8pt;
        font-weight: 700;
    }}
    QLabel#ConfidenceBadgeMid {{
        background: {bg3};
        color: {warning};
        border: 1px solid {warning};
        border-radius: 10px;
        padding: 2px 8px;
        font-size: 8pt;
        font-weight: 700;
    }}
    QLabel#ConfidenceBadgeLow {{
        background: {bg3};
        color: {text2};
        border: 1px solid {border};
        border-radius: 10px;
        padding: 2px 8px;
        font-size: 8pt;
        font-size: 8pt;
        font-weight: 700;
    }}

    /* ── Separator ──────────────────────────────────────────────── */
    QFrame#Separator {{
        background: {border};
        border: none;
        max-height: 1px;
    }}

    /* ── Brain widget (Phase 9 — ARIA Brain highlight) ──────────────── */
    QFrame#BrainWidget {{
        background: {bg2};
        border: 1px solid {border};
        border-left: 3px solid {accent};
        border-radius: 6px;
    }}
    QFrame#BrainWidget[active="preview"] {{
        border-left-color: {warning};
    }}
    QFrame#BrainWidget[active="pending"] {{
        border-left-color: {accent};
    }}
    QWidget#StepCard {{
        background: transparent;
        border: none;
        border-left: 3px solid {kind_thought};
        border-radius: 0px;
    }}
    QWidget#StepCard[kind="thought"] {{
        border-left-color: {kind_thought};
    }}
    QWidget#StepCard[kind="plan"] {{
        border-left-color: {kind_plan};
    }}
    QWidget#StepCard[kind="action"] {{
        border-left-color: {kind_action};
    }}
    QWidget#StepCard[kind="observation"] {{
        border-left-color: {kind_observation};
    }}
    QLabel#StepKind {{
        font-size: 8.5pt;
        font-weight: 700;
        letter-spacing: 0.5px;
    }}
    QLabel#StepKind[kind="thought"] {{
        color: {kind_thought};
    }}
    QLabel#StepKind[kind="plan"] {{
        color: {kind_plan};
    }}
    QLabel#StepKind[kind="action"] {{
        color: {kind_action};
    }}
    QLabel#StepKind[kind="observation"] {{
        color: {kind_observation};
    }}
    QLabel#StepTime {{
        color: {dim};
        font-size: 8pt;
        font-family: 'Cascadia Code', 'Consolas', monospace;
    }}
    QLabel#StepToolName {{
        color: {text};
        font-family: 'Cascadia Code', 'Consolas', monospace;
        font-size: 8.5pt;
        font-weight: 700;
    }}
    QLabel#StepContent {{
        color: {text};
        font-size: 9.5pt;
    }}
    QLabel#StepArgs, QLabel#StepResult {{
        color: {text2};
        font-family: 'Cascadia Code', 'Consolas', monospace;
        font-size: 8pt;
    }}
    QLabel#StepExecutedOk {{
        color: {success};
        font-size: 8pt;
        font-weight: 700;
    }}
    QLabel#StepExecutedNo {{
        color: {error};
        font-size: 8pt;
        font-weight: 700;
    }}

    QWidget#PlanCard {{
        background: {bg2};
        border: 1px solid {border};
        border-left: 3px solid {kind_plan};
        border-radius: 6px;
    }}
    QLabel#PlanTitle {{
        color: {kind_plan};
        font-weight: 700;
        font-size: 9.5pt;
        letter-spacing: 0.5px;
    }}
    QLabel#PlanBody {{
        color: {text};
        font-family: 'Cascadia Code', 'Consolas', monospace;
        font-size: 9pt;
    }}

    QWidget#ApprovalCard {{
        background: {bg2};
        border: 1px solid {warning};
        border-left: 3px solid {warning};
        border-radius: 6px;
    }}
    QLabel#ApprovalTitle {{
        color: {warning};
        font-weight: 700;
        font-size: 9.5pt;
    }}
    QLabel#ApprovalSummary {{
        color: {text};
        font-size: 9.5pt;
    }}
    QLabel#ApprovalRisk {{
        color: {error};
        font-size: 8pt;
        font-weight: 700;
    }}

    QWidget#TaskRow {{
        background: transparent;
        border-bottom: 1px solid {border};
    }}
    QWidget#TaskRow:hover {{
        background: {row_hover};
    }}
    QLabel#TaskRowGoal {{
        color: {text};
        font-size: 9.5pt;
        font-weight: 600;
    }}
    QLabel#TaskRowMeta {{
        color: {text2};
        font-size: 8pt;
    }}
    QLabel#TaskRowId {{
        color: {dim};
        font-family: 'Cascadia Code', 'Consolas', monospace;
        font-size: 8pt;
    }}

    /* ── Settings dialog (Phase 6) ──────────────────────────────── */
    QWidget#SettingsBox {{
        background: {bg};
        border: 1px solid {border};
        border-radius: 8px;
    }}
    QWidget#SettingsTB {{
        background: {bg2};
        border: none;
        border-bottom: 1px solid {border};
    }}
    QWidget#SettingsFoot {{
        background: {bg2};
        border: none;
        border-top: 1px solid {border};
    }}
    QLabel#SettingsSection {{
        color: {text2};
        font-size: 8pt;
        font-weight: 700;
        letter-spacing: 1.5px;
    }}
    QLabel#SettingsLabel {{
        color: {text2};
        font-size: 9.5pt;
    }}
    QFrame#SettingsDivider {{
        background: {border};
        border: none;
        max-height: 1px;
    }}
    QPushButton#SCloseBtn, QPushButton#SCancelBtn {{
        background: transparent;
        color: {text2};
        border: none;
        font-size: 9pt;
        padding: 6px 12px;
        border-radius: 4px;
    }}
    QPushButton#SCloseBtn:hover, QPushButton#SCancelBtn:hover {{
        background: {row_hover};
        color: {text};
    }}
    QPushButton#SApplyBtn {{
        background: {accent};
        color: {accent_text};
        border: none;
        border-radius: 4px;
        padding: 6px 14px;
        font-weight: 700;
    }}
    QPushButton#SApplyBtn:hover {{
        background: {accent2};
    }}
    QLabel#SettingsPreview {{
        color: {dim};
        font-size: 9pt;
        font-family: 'Cascadia Code', 'Consolas', monospace;
    }}
    QComboBox#SettingsCombo, QSpinBox#SettingsSpin, QLineEdit#SettingsLine {{
        background: {bg3};
        color: {text};
        border: 1px solid {border};
        border-radius: 4px;
        padding: 4px 8px;
    }}
    QCheckBox#SettingsCheck {{
        color: {text};
        spacing: 6px;
    }}
    QCheckBox#SettingsCheck::indicator {{
        width: 14px;
        height: 14px;
        border: 1px solid {border};
        border-radius: 3px;
        background: {bg3};
    }}
    QCheckBox#SettingsCheck::indicator:checked {{
        background: {accent};
        border-color: {accent};
    }}

    /* ── Command palette, confirm dialog, shortcuts ─────────────── */
    QWidget#CommandPalette, QWidget#ConfirmDialog, QWidget#KeyboardShortcutsHelp {{
        background: {bg};
        border: 1px solid {border};
        border-radius: 8px;
    }}

    /* Settings dialog color cards */
    QWidget#ColorCard {{
        background: {bg2};
        border: 1px solid {border};
        border-radius: 8px;
    }}
    QWidget#ColorCard:hover {{
        border-color: {accent};
    }}
    QWidget#ColorCard[selected="true"] {{
        border-color: {accent};
        border-width: 2px;
    }}
    QLineEdit#CommandPaletteInput {{
        background: transparent;
        border: none;
        border-bottom: 1px solid {border};
        padding: 8px 12px;
        font-size: 10pt;
        color: {text};
    }}
    QListWidget#CommandPaletteList {{
        background: transparent;
        border: none;
        color: {text};
        padding: 4px 0;
        outline: 0;
    }}
    QListWidget#CommandWidgetCommandPaletteList::item {{
        padding: 6px 12px;
    }}
    QListWidget#CommandPaletteList::item {{
        padding: 6px 12px;
    }}
    QListWidget#CommandPaletteList::item:selected {{
        background: {row_hover};
        color: {accent};
    }}
    QLabel#DialogTitle {{
        color: {text};
        font-size: 11pt;
        font-weight: 700;
    }}
    QLabel#DialogMessage {{
        color: {text2};
        font-size: 9.5pt;
    }}
    QPushButton#DialogBtn {{
        background: {bg2};
        color: {text};
        border: 1px solid {border};
        border-radius: 4px;
        padding: 6px 14px;
    }}
    QPushButton#DialogBtn:hover {{
        background: {row_hover};
        border-color: {accent};
    }}
    QPushButton#DialogBtnPrimary {{
        background: {accent};
        color: {accent_text};
        border: none;
        border-radius: 4px;
        padding: 6px 14px;
        font-weight: 700;
    }}
    QPushButton#DialogBtnPrimary:hover {{
        background: {accent2};
    }}
    """