import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: timing
    property var editor: studio.markup
    spacing: 7
    Text { text: "Time on screen"; color: "#9DAFC2"; font.pixelSize: 11 }
    Flow {
        Layout.fillWidth: true; Layout.preferredHeight: implicitHeight; spacing: 4
        Repeater {
            model: [0,1,2,4]
            ActionButton {
                required property int modelData
                text: modelData===0 ? "Freeze" : modelData+"s"
                highlighted: !timing.editor.selected.keep && timing.editor.selected.linger===modelData
                onClicked: timing.editor.edit('linger',modelData)
            }
        }
        ActionButton { text: "Stay on"; highlighted: !!timing.editor.selected.keep; onClicked: timing.editor.edit('keep',true) }
    }
    MarkupTimingField { Layout.fillWidth: true; editor: timing.editor; field: "linger"; label: "Custom display duration (0–30 s)"; maximum: 30 }
    MarkupTimingField { Layout.fillWidth: true; editor: timing.editor; field: "t"; label: "Source time (seconds)"; maximum: studio.duration }
    ActionButton { objectName: "markup-time-playhead"; text: "Set time to playhead"; onClicked: timing.editor.edit('t',studio.position) }
    Text {
        text: "0 shows only at the freeze. Stay on continues from the markup time. Moving a tracked ring also shifts its tracking times."
        color: "#9DAFC2"; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true
    }
}
