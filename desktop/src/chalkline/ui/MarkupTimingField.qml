import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: timing
    property var editor
    property string field
    property string label
    property real maximum: 30
    property bool dirty: false
    property int capturedKey: -1
    function refresh(force) {
        if (!force && input.activeFocus && dirty) return
        const value=editor.selected[field]
        input.text=value===undefined ? "" : Number(value).toFixed(2)
        capturedKey=editor.timingEditKey
        dirty=false
    }
    Component.onCompleted: refresh(true)
    Connections { target: timing.editor; function onChanged() { timing.refresh(false) } }
    Label { text: timing.label; font.pixelSize: 11 }
    RowLayout {
        Layout.fillWidth: true
        TextField {
            id: input
            objectName: "markup-timing-"+timing.field
            Layout.fillWidth: true; Layout.minimumWidth: 0
            placeholderText: timing.field==="linger" ? "Default / Stay on" : "Source seconds"
            validator: DoubleValidator { bottom: 0; top: timing.maximum; decimals: 2; locale: "C"; notation: DoubleValidator.StandardNotation }
            onTextEdited: {
                if (!timing.dirty) timing.capturedKey=timing.editor.timingEditKey
                timing.dirty=true
            }
            onAccepted: apply.clicked()
        }
        ActionButton {
            id: apply
            objectName: "markup-apply-"+timing.field
            text: "Apply"
            enabled: input.acceptableInput && input.text!=="" && timing.editor.selection>=0
            onClicked: {
                if (!enabled) return
                timing.editor.editTiming(timing.field,Number(input.text),timing.capturedKey)
                timing.refresh(true)
            }
        }
    }
}
