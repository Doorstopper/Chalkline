import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: panel
    spacing: 8
    property string storedColor: studio.notesStyle.color
    property string editorColor: storedColor
    onStoredColorChanged: editorColor = storedColor
    function setStyle(color, size, column, row) {
        editorColor = color
        studio.setNotesStyle(color,size,column,row)
    }
    Label { text: "NOTES"; color: "#9DAFC2"; font.pixelSize: 11 }
    TextArea {
        id: notes
        property bool syncing: false
        property bool ready: false
        property string knownDraft: ""
        property string clipKey: ""
        function display(value) {
            if (text === value) return
            syncing = true
            text = value
            syncing = false
        }
        function syncFromClip() {
            const value = studio.current.notes || ""
            const key = studio.notesEditorKey
            if (key !== clipKey || value !== knownDraft) {
                clipKey = key
                knownDraft = value
                display(value)
            }
        }
        function loadFreeze(explicit) {
            if (!explicit && activeFocus) return
            const context = studio.freezeNoteAtPlayhead(explicit)
            if (context.at === undefined) {
                if (explicit) studio.message("No freeze within half a second; notes kept.")
                return
            }
            studio.finishNotesEdit()
            display(context.text)
            if (context.color) panel.editorColor = context.color
            if (explicit) studio.message(context.text ? "Loaded notes from this freeze." : "This freeze has no notes yet.")
        }
        placeholderText: "Write coaching notes…"
        Layout.fillWidth: true; wrapMode: TextEdit.Wrap
        enabled: studio.selection>=0
        Component.onCompleted: { syncFromClip(); ready = true }
        onTextChanged: if (ready && !syncing) studio.setNotesDraft(text)
        onActiveFocusChanged: if (!activeFocus) studio.finishNotesEdit()
        Connections {
            target: studio
            function onChanged() { notes.syncFromClip() }
            function onNotesSyncRequested() { notes.loadFreeze(false) }
        }
    }
    RowLayout {
        ComboBox {
            Layout.fillWidth: true
            model: ["Us", "Them", "Space", "Path", "White"]
            currentIndex: ["ours","theirs","space","path","ball"].indexOf(panel.editorColor)
            onActivated: setStyle(["ours","theirs","space","path","ball"][currentIndex],studio.notesStyle.size,studio.notesStyle.column,studio.notesStyle.row)
        }
        SpinBox {
            from: 10; to: 60; value: studio.notesStyle.size
            onValueModified: setStyle(panel.editorColor,value,studio.notesStyle.column,studio.notesStyle.row)
            ToolTip.visible: hovered; ToolTip.text: "Notes text size"
        }
    }
    GridLayout {
        columns: 3; Layout.fillWidth: true
        Repeater {
            model: ["Top left","Top centre","Top right","Middle left","Centre","Middle right","Bottom left","Bottom centre","Bottom right"]
            Button {
                required property string modelData
                required property int index
                Layout.fillWidth: true; implicitWidth: 48
                text: ["↖","↑","↗","←","•","→","↙","↓","↘"][index]
                highlighted: studio.notesStyle.column===index%3 && studio.notesStyle.row===Math.floor(index/3)
                ToolTip.visible: hovered; ToolTip.text: modelData
                Accessible.name: modelData
                onClicked: setStyle(panel.editorColor,studio.notesStyle.size,index%3,Math.floor(index/3))
            }
        }
    }
    Button { text: "Apply at freeze"; Layout.fillWidth: true; enabled: studio.selection>=0 && !studio.busy; onClicked: studio.applyNotes("freeze",notes.text,panel.editorColor) }
    Button { text: "Apply to whole clip"; Layout.fillWidth: true; enabled: studio.selection>=0 && !studio.busy; onClicked: studio.applyNotes("clip",notes.text,panel.editorColor) }
    Button { text: "Load text at this freeze"; Layout.fillWidth: true; enabled: studio.selection>=0; onClicked: notes.loadFreeze(true) }
}
