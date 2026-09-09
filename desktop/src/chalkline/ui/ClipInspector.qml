import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    objectName: "clipInspector"
    property var workspace
    spacing: 10
    GroupBox {
        title: "Drawing tools"; Layout.fillWidth: true
        MarkupPanel { width: parent.width }
    }
    GroupBox {
        title: "Clip details"; Layout.fillWidth: true
        ColumnLayout {
            width: parent.width; spacing: 8
            TextField { text: studio.current.label || ""; placeholderText: "Clip label"; Layout.fillWidth: true; enabled: studio.selection>=0; onEditingFinished: studio.setText("label",text) }
            TextField { text: studio.current.caption || ""; placeholderText: "Caption"; Layout.fillWidth: true; enabled: studio.selection>=0; onEditingFinished: studio.setText("caption",text) }
            Text { text: (studio.current.caption || "").trim().split(/\s+/).filter(Boolean).length+" words / aim for 15"; color: "#9DAFC2"; font.pixelSize: 11 }
            ComboBox {
                Layout.fillWidth: true; model: studio.pads; textRole: "label"; enabled: studio.selection>=0
                currentIndex: studio.current.padIndex===undefined ? -1 : studio.current.padIndex
                displayText: "Category: " + (studio.current.label || "Choose")
                onActivated: studio.recategorize(currentIndex)
            }
            ComboBox {
                Layout.fillWidth: true; model: ["No kind", "Highlight", "Learning"]; enabled: studio.selection>=0
                currentIndex: ["", "highlight", "learning"].indexOf(studio.current.kind || "")
                onActivated: studio.setKind(["", "highlight", "learning"][currentIndex])
            }
            TextField { text: studio.currentPlayers; placeholderText: "Players, separated by commas"; Layout.fillWidth: true; enabled: studio.selection>=0; onEditingFinished: studio.setPlayers(text) }
            TextField { text: studio.current.ask || ""; placeholderText: "Coaching prompt"; Layout.fillWidth: true; enabled: studio.selection>=0; onEditingFinished: studio.setText("ask",text) }
            Button { text: "Delete clip"; Layout.fillWidth: true; enabled: studio.selection>=0 && !studio.busy; onClicked: studio.deleteCurrent() }
        }
    }
    GroupBox {
        title: "Coaching notes"; Layout.fillWidth: true
        ColumnLayout {
            width: parent.width; spacing: 8
            NotesPanel { Layout.fillWidth: true }
        }
    }
    GroupBox {
        title: "Freeze & slow motion"; Layout.fillWidth: true
        ColumnLayout {
            width: parent.width; spacing: 8
            Text { text: "Before / after (seconds)"; color: "#9DAFC2"; font.pixelSize: 11 }
            RowLayout {
                TextField { id: before; text: studio.current.pre===undefined ? "2" : studio.current.pre; Layout.fillWidth: true; validator: DoubleValidator { bottom: 0; top: 3600 } onEditingFinished: studio.setTrim(Number(text),Number(after.text)) }
                TextField { id: after; text: studio.current.post===undefined ? "7" : studio.current.post; Layout.fillWidth: true; validator: DoubleValidator { bottom: 0; top: 3600 } onEditingFinished: studio.setTrim(Number(before.text),Number(text)) }
            }
            TimingPanel { Layout.fillWidth: true }
        }
    }
    GroupBox {
        title: "Export"; Layout.fillWidth: true
        ColumnLayout {
            width: parent.width; spacing: 8
            Button {
                text: "Export true 4K"; Layout.fillWidth: true
                enabled: studio.selection>=0 && !studio.busy
                highlighted: true; onClicked: studio.export()
            }
            ProgressBar { Layout.fillWidth: true; value: studio.progress; visible: studio.busy }
            Button { text: "Cancel export"; visible: studio.busy; Layout.fillWidth: true; onClicked: studio.cancelExport() }
            Text { text: "3840 × 2160 · H.264 MP4\nRendered from original footage."; color: "#9DAFC2"; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        }
    }
}
