# styles.py — Frosted Glass Theme Engine for ARIA
# All styling uses semi-transparent rgba values over a dark painted background.
# The theme dict `t` is accepted for API compatibility but the glass theme
# is intentionally fixed — every panel, input, button, and label uses the
# same translucent white-on-dark vocabulary for visual cohesion.

def build_stylesheet(t: dict) -> str:
    """Return the global QSS frosted-glass stylesheet.

    `t` is the legacy theme dict from constants.py — kept for call-site
    compatibility but the frosted glass look is theme-agnostic.
    """
    return """
    /* ═══════════════════════════════════════════════════════════════
       FROSTED GLASS THEME — ARIA Desktop
       ═══════════════════════════════════════════════════════════════ */

    /* ── Core Surfaces ──────────────────────────────────────────── */
    QMainWindow {
        background: transparent;
    }
    QDialog {
        background: rgba(255, 255, 255, 0.08);
    }
    QWidget {
        background: rgba(255, 255, 255, 0.08);
        color: rgba(255, 255, 255, 0.9);
        font-family: 'Segoe UI Variable', 'Segoe UI', 'SF Pro Text', sans-serif;
        font-size: 10pt;
    }

    /* Glow effect for active elements */
    .glow-active {
        border: 1px solid rgba(120, 180, 255, 0.5);
    }

    /* Stacked widget and transparent containers */
    QStackedWidget {
        background: transparent;
        border: none;
    }

    /* ── Structural Panels (TitleBar, Sidebar, etc.) ─────────────── */
    QWidget#TitleBar {
        background: rgba(255, 255, 255, 0.04);
        border: none;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }
    QWidget#Sidebar {
        background: rgba(255, 255, 255, 0.03);
        border: none;
        border-right: 1px solid rgba(255, 255, 255, 0.06);
    }
    QWidget#StatusBar {
        background: rgba(255, 255, 255, 0.04);
        border: none;
        border-top: 1px solid rgba(255, 255, 255, 0.08);
    }

    /* Page backgrounds — fully transparent so the painted gradient shows */
    QWidget#ChatPage, QWidget#TerminalPage, QWidget#TimelinePage,
    QWidget#WarningsPage, QWidget#SelfModPage, QWidget#PatternsPage {
        background: transparent;
    }

    /* ── Glass Panels (Quick / System side panels) ──────────────── */
    QWidget#GlassPanel {
        background: rgba(255, 255, 255, 0.10);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 16px;
    }
    QWidget#GlassPanel:hover {
        background: rgba(255, 255, 255, 0.14);
        border-color: rgba(120, 180, 255, 0.30);
    }
    QWidget#GlassPanelHeader {
        background: transparent;
        border: none;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px 16px 0 0;
    }
    QLabel#GlassPanelTitle {
        color: rgba(255, 255, 255, 0.45);
        font-size: 8pt;
        font-weight: 700;
        letter-spacing: 3px;
        font-family: 'Cascadia Code', 'Consolas', monospace;
        background: transparent;
    }

    /* ── QFrame Panels ──────────────────────────────────────────── */
    QFrame {
        background: rgba(255, 255, 255, 0.15);
        border: 1px solid rgba(255, 255, 255, 0.25);
        border-radius: 12px;
    }
    /* Horizontal / vertical line separators */
    QFrame[frameShape="4"], QFrame[frameShape="5"] {
        background: rgba(255, 255, 255, 0.12);
        border: none;
        border-radius: 0px;
        max-height: 1px;
    }

    /* ── Labels ─────────────────────────────────────────────────── */
    QLabel {
        color: rgba(255, 255, 255, 0.9);
        background: transparent;
        border: none;
    }

    /* Title bar labels */
    QLabel#TitleLogo {
        color: rgba(120, 180, 255, 0.9);
        font-size: 18px;
        font-weight: 700;
    }
    QLabel#TitleLabel {
        color: rgba(255, 255, 255, 0.92);
        font-size: 11pt;
        font-weight: 700;
        letter-spacing: 5px;
        font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif;
    }
    QLabel#TitleSubtitle {
        color: rgba(255, 255, 255, 0.40);
        font-size: 8.5pt;
    }
    QLabel#RailLogo {
        color: rgba(120, 180, 255, 0.9);
        font-size: 22px;
        font-weight: 800;
    }

    /* Section headers */
    QLabel#SectionHeader {
        color: rgba(255, 255, 255, 0.92);
        font-size: 14pt;
        font-weight: 700;
        font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif;
    }

    /* Chat bubbles */
    QLabel#AiBubble {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 rgba(255, 255, 255, 0.08), stop:1 rgba(255, 255, 255, 0.05));
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 18px;
        border-top-left-radius: 6px;
        padding: 16px 20px;
        color: rgba(255, 255, 255, 0.92);
        font-size: 10pt;
    }
    QLabel#AiBubble:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 rgba(255, 255, 255, 0.14), stop:1 rgba(255, 255, 255, 0.10));
        border-color: rgba(120, 180, 255, 0.30);
    }
    QLabel#UserBubble {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 rgba(100, 140, 255, 0.2), stop:1 rgba(120, 100, 255, 0.15));
        border: 1px solid rgba(100, 140, 255, 0.25);
        border-radius: 18px;
        border-top-right-radius: 6px;
        padding: 16px 20px;
        color: rgba(255, 255, 255, 0.95);
        font-size: 10pt;
    }
    QLabel#UserBubble:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 rgba(100, 160, 255, 0.28), stop:1 rgba(140, 100, 255, 0.22));
        border-color: rgba(120, 180, 255, 0.45);
    }

    /* Message container */
    QWidget#ChatArea {
        background: transparent;
        border: none;
    }
    QLabel#MessageRole {
        color: rgba(255, 255, 255, 0.40);
        font-size: 7.5pt;
        font-weight: 600;
        letter-spacing: 1.5px;
    }
    QLabel#TypingIndicator {
        color: rgba(120, 180, 255, 0.8);
        font-size: 8.5pt;
        font-style: italic;
        padding: 6px 16px;
    }

    /* Loading spinner */
    QLabel#LoadingSpinner {
        color: rgba(120, 180, 255, 0.9);
        font-size: 16pt;
    }
    QLabel#STTStatus {
        color: rgba(120, 180, 255, 0.85);
        font-size: 8pt;
        padding: 4px 16px;
    }

    /* Status bar labels */
    QLabel#StatusDot {
        color: rgba(80, 200, 120, 0.9);
        font-size: 9px;
    }
    QLabel#StatusDotOffline {
        color: rgba(255, 80, 80, 0.9);
        font-size: 9px;
    }
    QLabel#StatusLabel {
        color: rgba(255, 255, 255, 0.50);
        font-size: 8pt;
    }
    QLabel#LLMLabel {
        color: rgba(255, 255, 255, 0.40);
        font-size: 7.5pt;
        font-family: 'Cascadia Code', 'Consolas', monospace;
    }
    QLabel#NotifDot {
        color: rgba(255, 80, 80, 0.9);
        font-size: 8px;
        font-weight: 800;
    }

    /* Stat labels inside sidebar / system panel */
    QLabel#RailStatBar {
        background: rgba(255, 255, 255, 0.06);
        border-radius: 2px;
    }

    /* Timeline / Warnings labels */
    QLabel#TimelineTime {
        color: rgba(255, 255, 255, 0.35);
        font-size: 8pt;
        font-family: 'Cascadia Code', 'Consolas', monospace;
    }
    QLabel#TimelineText {
        color: rgba(255, 255, 255, 0.85);
        font-size: 9pt;
    }

    /* Pattern page labels */
    QLabel#PatternCardName {
        color: rgba(255, 255, 255, 0.92);
        font-size: 9.5pt;
        font-weight: 600;
    }
    QLabel#PatternCardSlug {
        color: rgba(120, 180, 255, 0.7);
        font-size: 8pt;
        font-family: 'Cascadia Code', 'Consolas', monospace;
    }
    QLabel#PatternCardPreview {
        color: rgba(255, 255, 255, 0.40);
        font-size: 8pt;
    }
    QLabel#PatternCount {
        color: rgba(255, 255, 255, 0.40);
        font-size: 8pt;
        font-family: 'Cascadia Code', 'Consolas', monospace;
    }
    QLabel#PatternStatus {
        color: rgba(255, 255, 255, 0.40);
        font-size: 8pt;
        font-family: 'Cascadia Code', 'Consolas', monospace;
    }

    /* Proposal / SelfMod labels */
    QLabel#ProposalTitle {
        color: rgba(255, 255, 255, 0.92);
        font-size: 10pt;
        font-weight: 600;
    }
    QLabel#ProposalText {
        color: rgba(255, 255, 255, 0.75);
        font-size: 9pt;
    }
    QLabel#ProposalMeta {
        color: rgba(255, 255, 255, 0.40);
        font-size: 8pt;
    }

    /* ── Buttons ────────────────────────────────────────────────── */
    QPushButton {
        background: rgba(255, 255, 255, 0.18);
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.30);
        border-radius: 8px;
        padding: 6px 14px;
        font-size: 9pt;
    }
    QPushButton:hover {
        background: rgba(255, 255, 255, 0.28);
        border-color: rgba(120, 180, 255, 0.55);
    }
    QPushButton:pressed {
        background: rgba(120, 180, 255, 0.25);
        border-color: rgba(120, 180, 255, 0.7);
    }
    QPushButton:disabled {
        background: rgba(255, 255, 255, 0.08);
        color: rgba(255, 255, 255, 0.3);
        border-color: rgba(255, 255, 255, 0.1);
    }

    /* Title / Rail buttons — borderless icons */
    QPushButton#TitleBtn {
        background: transparent;
        color: rgba(255, 255, 255, 0.50);
        border: none;
        font-size: 12pt;
        padding: 0;
        border-radius: 6px;
    }
    QPushButton#TitleBtn:hover {
        background: rgba(255, 255, 255, 0.12);
        color: rgba(255, 255, 255, 0.85);
    }
    QPushButton#TitleBtnClose {
        background: transparent;
        color: rgba(255, 255, 255, 0.50);
        border: none;
        font-size: 11pt;
        padding: 0;
        border-radius: 6px;
    }
    QPushButton#TitleBtnClose:hover {
        background: rgba(255, 60, 60, 0.40);
        color: #ff9090;
    }
    QPushButton#TitleBtnSettings {
        background: transparent;
        color: rgba(255, 255, 255, 0.50);
        border: none;
        font-size: 14pt;
        padding: 0;
        border-radius: 6px;
    }
    QPushButton#TitleBtnSettings:hover {
        background: rgba(255, 255, 255, 0.12);
        color: rgba(120, 180, 255, 0.9);
    }

    /* Sidebar nav buttons */
    QPushButton#RailBtn {
        background: transparent;
        color: rgba(255, 255, 255, 0.40);
        border: none;
        border-radius: 14px;
        font-size: 18px;
        padding: 0;
    }
    QPushButton#RailBtn:hover {
        background: rgba(255, 255, 255, 0.12);
        color: rgba(120, 180, 255, 0.95);
    }
    QPushButton#RailBtnActive {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 rgba(120, 180, 255, 0.18), stop:1 rgba(140, 80, 255, 0.12));
        color: rgba(120, 180, 255, 0.95);
        border: 1px solid rgba(120, 180, 255, 0.40);
        border-radius: 14px;
        font-size: 18px;
        padding: 0;
    }
    QPushButton#RailBtnActive:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 rgba(120, 180, 255, 0.28), stop:1 rgba(140, 80, 255, 0.22));
    }

    /* Send button */
    QPushButton#SendBtn {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 rgba(80, 140, 255, 0.85), stop:1 rgba(140, 80, 255, 0.85));
        color: #ffffff;
        border: none;
        border-radius: 14px;
        padding: 10px 20px;
        font-weight: 700;
        font-size: 10pt;
    }
    QPushButton#SendBtn:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 rgba(100, 160, 255, 0.95), stop:1 rgba(160, 100, 255, 0.95));
        border: 1px solid rgba(255, 255, 255, 0.45);
    }
    QPushButton#SendBtn:pressed {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 rgba(60, 120, 255, 0.95), stop:1 rgba(120, 60, 255, 0.95));
    }
    QPushButton#SendBtn:disabled {
        background: rgba(255, 255, 255, 0.1);
        color: rgba(255, 255, 255, 0.3);
    }

    /* Suggestion chips */
    QPushButton#SuggestionBtn {
        background: rgba(255, 255, 255, 0.08);
        color: rgba(255, 255, 255, 0.55);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 16px;
        padding: 5px 12px;
        font-size: 8pt;
    }
    QPushButton#SuggestionBtn:hover {
        background: rgba(120, 180, 255, 0.15);
        color: rgba(120, 180, 255, 0.95);
        border-color: rgba(120, 180, 255, 0.40);
    }
    QPushButton#SuggestionBtn:pressed {
        background: rgba(120, 180, 255, 0.25);
    }

    /* Quick action buttons */
    QPushButton#QuickBtn {
        background: rgba(255, 255, 255, 0.10);
        color: rgba(255, 255, 255, 0.75);
        border: 1px solid rgba(255, 255, 255, 0.18);
        border-radius: 12px;
        font-size: 9pt;
        padding: 8px 4px;
        text-align: center;
    }
    QPushButton#QuickBtn:hover {
        background: rgba(120, 180, 255, 0.18);
        color: rgba(120, 180, 255, 0.95);
        border-color: rgba(120, 180, 255, 0.40);
    }
    QPushButton#QuickBtn:pressed {
        background: rgba(120, 180, 255, 0.10);
    }

    /* Approve / Reject / Analyze buttons */
    QPushButton#ApproveBtn {
        background: rgba(80, 200, 120, 0.12);
        color: rgba(80, 200, 120, 0.9);
        border: 1px solid rgba(80, 200, 120, 0.35);
        border-radius: 10px;
        padding: 8px 18px;
        font-weight: 600;
    }
    QPushButton#ApproveBtn:hover {
        background: rgba(80, 200, 120, 0.25);
    }
    QPushButton#RejectBtn {
        background: rgba(255, 80, 80, 0.08);
        color: rgba(255, 80, 80, 0.85);
        border: 1px solid rgba(255, 80, 80, 0.25);
        border-radius: 10px;
        padding: 8px 18px;
    }
    QPushButton#RejectBtn:hover {
        background: rgba(255, 80, 80, 0.20);
    }
    QPushButton#AnalyzeBtn {
        background: rgba(120, 180, 255, 0.12);
        color: rgba(120, 180, 255, 0.9);
        border: 1px solid rgba(120, 180, 255, 0.35);
        border-radius: 10px;
        padding: 8px 18px;
        font-weight: 600;
    }
    QPushButton#AnalyzeBtn:hover {
        background: rgba(120, 180, 255, 0.25);
    }
    QPushButton#RollbackBtn {
        background: rgba(255, 255, 255, 0.08);
        color: rgba(255, 255, 255, 0.55);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 8px;
        padding: 4px 10px;
    }
    QPushButton#RollbackBtn:hover {
        color: rgba(255, 255, 255, 0.85);
        border-color: rgba(120, 180, 255, 0.40);
    }
    QPushButton#ClearWarningsBtn {
        background: rgba(255, 255, 255, 0.08);
        color: rgba(255, 255, 255, 0.55);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 10px;
        padding: 6px 14px;
    }
    QPushButton#ClearWarningsBtn:hover {
        color: rgba(255, 255, 255, 0.85);
        border-color: rgba(120, 180, 255, 0.40);
    }

    /* Pattern page buttons */
    QPushButton#PatternRunBtn {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 rgba(80, 200, 120, 0.6), stop:1 rgba(80, 140, 255, 0.6));
        color: #ffffff;
        border: none;
        border-radius: 12px;
        padding: 10px 0;
        font-weight: 700;
    }
    QPushButton#PatternRunBtn:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 rgba(80, 140, 255, 0.75), stop:1 rgba(80, 200, 120, 0.75));
    }
    QPushButton#PatternRunBtn:disabled {
        background: rgba(255, 255, 255, 0.06);
        color: rgba(255, 255, 255, 0.25);
    }
    QPushButton#PatternActionBtn {
        background: rgba(255, 255, 255, 0.08);
        color: rgba(255, 255, 255, 0.55);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 8px;
        padding: 5px 12px;
    }
    QPushButton#PatternActionBtn:hover {
        color: rgba(255, 255, 255, 0.85);
        border-color: rgba(120, 180, 255, 0.40);
    }
    QPushButton#PatternToggleBtn {
        background: transparent;
        color: rgba(255, 255, 255, 0.40);
        border: none;
        text-align: left;
        font-size: 8pt;
        padding: 2px 0;
    }
    QPushButton#PatternToggleBtn:hover {
        color: rgba(255, 255, 255, 0.75);
    }

    /* ── Inputs ─────────────────────────────────────────────────── */
    QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {
        background: rgba(255, 255, 255, 0.10);
        border: 1px solid rgba(255, 255, 255, 0.20);
        border-radius: 6px;
        color: white;
        padding: 4px;
        selection-background-color: rgba(120, 180, 255, 0.35);
    }
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
        border: 1px solid rgba(120, 180, 255, 0.65);
        background: rgba(255, 255, 255, 0.14);
    }
    QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover, QComboBox:hover {
        border-color: rgba(255, 255, 255, 0.32);
    }

    /* Chat input */
    QLineEdit#ChatInput {
        background: rgba(255, 255, 255, 0.12);
        border: 1px solid rgba(255, 255, 255, 0.20);
        border-radius: 14px;
        padding: 10px 16px;
        font-size: 10pt;
    }
    QLineEdit#ChatInput:focus {
        border-color: rgba(120, 180, 255, 0.65);
        background: rgba(255, 255, 255, 0.16);
    }
    QLineEdit#ChatInput:hover {
        border-color: rgba(255, 255, 255, 0.32);
    }
    QLineEdit#ChatInput::placeholder {
        color: rgba(255, 255, 255, 0.35);
    }

    /* Keyboard shortcut hint */
    QLabel#ShortcutHint {
        color: rgba(255, 255, 255, 0.25);
        font-size: 7pt;
        font-family: 'Cascadia Code', 'Consolas', monospace;
    }

    /* Terminal */
    QPlainTextEdit#TerminalOutput {
        background: rgba(0, 0, 0, 0.25);
        color: rgba(0, 255, 200, 0.9);
        border: 1px solid rgba(255, 255, 255, 0.10);
        border-radius: 14px;
        padding: 16px;
        font-size: 9pt;
        font-family: 'Cascadia Code', 'JetBrains Mono', 'Consolas', monospace;
    }
    QPlainTextEdit#TerminalOutput:hover {
        border-color: rgba(120, 180, 255, 0.25);
    }
    QLineEdit#TerminalInput {
        background: rgba(255, 255, 255, 0.10);
        border: 1px solid rgba(255, 255, 255, 0.18);
        border-radius: 12px;
        padding: 10px 14px;
        font-family: 'Cascadia Code', 'Consolas', monospace;
    }
    QLineEdit#TerminalInput:focus {
        border-color: rgba(120, 180, 255, 0.65);
    }
    QLineEdit#TerminalInput:hover {
        border-color: rgba(255, 255, 255, 0.32);
    }
    QLabel#TerminalPrompt {
        color: rgba(0, 255, 200, 0.85);
        font-family: 'Cascadia Code', monospace;
        font-size: 14pt;
        font-weight: 700;
    }

    /* Pattern page inputs */
    QLineEdit#PatternSearch {
        background: rgba(255, 255, 255, 0.10);
        border: 1px solid rgba(255, 255, 255, 0.18);
        border-radius: 12px;
        padding: 8px 12px;
    }
    QLineEdit#PatternSearch:focus {
        border-color: rgba(120, 180, 255, 0.65);
    }
    QLineEdit#PatternSearch:hover {
        border-color: rgba(255, 255, 255, 0.32);
    }
    QLineEdit#PatternInput {
        background: rgba(255, 255, 255, 0.10);
        border: 1px solid rgba(255, 255, 255, 0.18);
        border-radius: 12px;
        padding: 10px 14px;
    }
    QLineEdit#PatternInput:focus {
        border-color: rgba(120, 180, 255, 0.65);
    }
    QLineEdit#PatternInput:hover {
        border-color: rgba(255, 255, 255, 0.32);
    }
    QTextEdit#PatternOutput {
        background: rgba(255, 255, 255, 0.06);
        color: rgba(255, 255, 255, 0.88);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 14px;
        padding: 14px 16px;
    }
    QTextEdit#PatternOutput:hover {
        border-color: rgba(120, 180, 255, 0.25);
    }
    QTextEdit#PatternPromptPreview {
        background: rgba(255, 255, 255, 0.05);
        color: rgba(255, 255, 255, 0.45);
        border: 1px solid rgba(255, 255, 255, 0.10);
        border-radius: 10px;
        padding: 8px;
        font-family: 'Cascadia Code', 'Consolas', monospace;
        font-size: 8pt;
    }
    QTextEdit#PatternPromptPreview:hover {
        border-color: rgba(120, 180, 255, 0.22);
    }

    /* ── Scroll Areas ──────────────────────────────────────────── */
    QScrollArea {
        background: transparent;
        border: none;
    }
    QScrollArea > QWidget > QWidget {
        background: transparent;
    }

    /* ── Scrollbars ─────────────────────────────────────────────── */
    QScrollBar:vertical {
        background: transparent;
        width: 12px;
        margin: 4px;
    }
    QScrollBar::handle:vertical {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 rgba(120, 180, 255, 0.4), stop:1 rgba(140, 80, 255, 0.4));
        min-height: 40px;
        border-radius: 6px;
        margin: 2px;
    }
    QScrollBar::handle:vertical:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 rgba(120, 180, 255, 0.65), stop:1 rgba(140, 80, 255, 0.65));
    }
    QScrollBar::handle:vertical:pressed {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 rgba(80, 140, 255, 0.85), stop:1 rgba(140, 80, 255, 0.85));
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        background: rgba(255, 255, 255, 0.03);
        border-radius: 6px;
    }
    QScrollBar:horizontal {
        height: 0px;
    }

    /* ── Animated Buttons ─────────────────────────────────────────── */
    QPushButton {
        background: rgba(255, 255, 255, 0.18);
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.30);
        border-radius: 8px;
        padding: 6px 14px;
        font-size: 9pt;
    }
    QPushButton:hover {
        background: rgba(255, 255, 255, 0.28);
        border-color: rgba(120, 180, 255, 0.55);
    }
    QPushButton:pressed {
        background: rgba(120, 180, 255, 0.25);
        border-color: rgba(120, 180, 255, 0.7);
    }
    QPushButton:disabled {
        background: rgba(255, 255, 255, 0.08);
        color: rgba(255, 255, 255, 0.3);
        border-color: rgba(255, 255, 255, 0.1);
    }

    /* ── Menus ──────────────────────────────────────────────────── */
    QMenuBar, QMenu {
        background: rgba(20, 20, 40, 0.85);
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.15);
    }
    QMenu::item:selected {
        background: rgba(255, 255, 255, 0.15);
    }

    /* ── Tabs ───────────────────────────────────────────────────── */
    QTabWidget::pane {
        border: 1px solid rgba(255, 255, 255, 0.12);
        background: transparent;
        border-radius: 10px;
    }
    QTabBar::tab {
        background: rgba(255, 255, 255, 0.08);
        color: rgba(255, 255, 255, 0.55);
        border: 1px solid rgba(255, 255, 255, 0.12);
        padding: 7px 16px;
        margin: 2px;
        border-radius: 8px;
    }
    QTabBar::tab:selected {
        background: rgba(255, 255, 255, 0.22);
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.30);
    }
    QTabBar::tab:hover:!selected {
        background: rgba(255, 255, 255, 0.15);
        border-color: rgba(120, 180, 255, 0.28);
    }

    /* ── Tooltips ───────────────────────────────────────────────── */
    QToolTip {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 rgba(30, 35, 55, 0.95), stop:1 rgba(25, 30, 50, 0.95));
        color: rgba(255, 255, 255, 0.92);
        border: 1px solid rgba(120, 180, 255, 0.3);
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 8.5pt;
    }

    /* ── Timeline / Warning entry widgets ──────────────────────── */
    QWidget#TimelineEntry {
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 10px;
    }
    QWidget#TimelineEntry:hover {
        background: rgba(255, 255, 255, 0.12);
        border-color: rgba(120, 180, 255, 0.30);
    }
    QWidget#WarningEntryError {
        background: rgba(255, 60, 60, 0.06);
        border: 1px solid rgba(255, 60, 60, 0.20);
        border-left: 3px solid rgba(255, 60, 60, 0.60);
        border-radius: 10px;
    }
    QWidget#WarningEntryError:hover {
        background: rgba(255, 60, 60, 0.14);
    }
    QWidget#WarningEntryWarning {
        background: rgba(255, 180, 40, 0.06);
        border: 1px solid rgba(255, 180, 40, 0.20);
        border-left: 3px solid rgba(255, 180, 40, 0.60);
        border-radius: 10px;
    }
    QWidget#WarningEntryWarning:hover {
        background: rgba(255, 180, 40, 0.14);
    }
    QWidget#WarningEntryInfo {
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-left: 3px solid rgba(120, 180, 255, 0.60);
        border-radius: 10px;
    }
    QWidget#WarningEntryInfo:hover {
        background: rgba(255, 255, 255, 0.12);
        border-color: rgba(120, 180, 255, 0.40);
    }

    /* ── Proposal / Ledger cards ────────────────────────────────── */
    QWidget#ProposalCard {
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 14px;
    }
    QWidget#ProposalCard:hover {
        background: rgba(255, 255, 255, 0.14);
        border-color: rgba(120, 180, 255, 0.30);
    }
    QWidget#LedgerEntry {
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 10px;
    }
    QWidget#LedgerEntry:hover {
        background: rgba(255, 255, 255, 0.12);
        border-color: rgba(120, 180, 255, 0.30);
    }
    QWidget#LedgerEntryRolledBack {
        background: transparent;
        border: 1px dashed rgba(255, 255, 255, 0.15);
        border-radius: 10px;
    }
    QWidget#LedgerEntryRolledBack:hover {
        border-color: rgba(255, 180, 40, 0.45);
    }

    /* ── Pattern browser ───────────────────────────────────────── */
    QWidget#PatternBrowser {
        background: rgba(255, 255, 255, 0.04);
        border: none;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }
    QWidget#PatternCard {
        background: transparent;
        border: 1px solid transparent;
        border-radius: 12px;
    }
    QWidget#PatternCard:hover {
        background: rgba(255, 255, 255, 0.10);
        border-color: rgba(120, 180, 255, 0.30);
    }
    QWidget#PatternCardActive {
        background: rgba(120, 180, 255, 0.10);
        border: 1px solid rgba(120, 180, 255, 0.30);
        border-radius: 12px;
    }
    QWidget#PatternCardActive:hover {
        background: rgba(120, 180, 255, 0.18);
    }

    /* ── Input Area (chat bottom bar) ──────────────────────────── */
    QWidget#InputArea {
        background: rgba(255, 255, 255, 0.05);
        border: none;
        border-top: 1px solid rgba(255, 255, 255, 0.08);
    }
    QWidget#SuggestionsRow {
        background: transparent;
    }
    QWidget#ChatArea {
        background: transparent;
        border: none;
    }

    /* ── Settings Dialog ───────────────────────────────────────── */
    QWidget#SettingsBox {
        background: rgba(20, 25, 45, 0.95);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 20px;
    }
    QWidget#SettingsTB {
        background: rgba(255, 255, 255, 0.04);
        border: none;
        border-radius: 20px 20px 0 0;
    }
    QWidget#SettingsFoot {
        background: rgba(255, 255, 255, 0.04);
        border: none;
        border-radius: 0 0 20px 20px;
    }

    /* ── Stat bars (sidebar + system panel) ─────────────────────── */
    QFrame#RailStatBar {
        background: rgba(255, 255, 255, 0.06);
        border: none;
        border-radius: 2px;
    }
    QFrame#RailStatFill {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 rgba(80, 140, 255, 0.8), stop:1 rgba(140, 80, 255, 0.8));
        border: none;
        border-radius: 2px;
    }
    """