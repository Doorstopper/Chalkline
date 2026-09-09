import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: panel
    objectName: "markupPanel"
    property var editor: studio.markup
    spacing: 7
    enabled: !studio.busy
    Text { text: "Choose a tool, then drag on the video."; color: "#9DAFC2"; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
    GridLayout {
        Layout.fillWidth: true; columns: 2; columnSpacing: 4; rowSpacing: 4
        Repeater {
            model: [{key:"pan",label:"Pan"},{key:"arrow",label:"Arrow"},{key:"line",label:"Line"},
                    {key:"circle",label:"Circle"},{key:"pen",label:"Pen"},{key:"zone",label:"Zone"},
                    {key:"ground",label:"Ground ring"},{key:"text",label:"Text"}]
            ActionButton {
                required property var modelData
                objectName: "markup-tool-"+modelData.key
                Layout.fillWidth: true
                implicitHeight: 56
                text: modelData.key==="pan" ? "✋ Pan" : modelData.label
                display: AbstractButton.TextUnderIcon
                icon.source: modelData.key==="pan" ? "" : "icons/"+modelData.key+".svg"
                icon.width: 24; icon.height: 24
                icon.color: palette.buttonText
                highlighted: panel.editor.tool===modelData.key
                ToolTip.visible: hovered
                ToolTip.text: modelData.label
                enabled: modelData.key==="pan" || studio.selection>=0
                onClicked: panel.editor.setTool(modelData.key)
            }
        }
    }
    Text { text: "Colour · selected mark and new drawings"; color: "#9DAFC2"; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
    Flow {
        Layout.fillWidth: true; Layout.preferredHeight: implicitHeight; spacing: 4
        Repeater {
            model: [{key:"ours",label:"Us",color:"#50D890"},{key:"theirs",label:"Them",color:"#FF6B6B"},
                    {key:"space",label:"Space",color:"#FFC93C"},{key:"path",label:"Path",color:"#68BFFF"},
                    {key:"ball",label:"Ball",color:"#FFFFFF"},{key:"flood",label:"Flood",color:"#FFC93C"}]
            ActionButton {
                required property var modelData
                objectName: "markup-color-"+modelData.key
                text: modelData.label; palette.buttonText: modelData.color
                highlighted: panel.editor.color===modelData.key
                onClicked: panel.editor.setColor(modelData.key)
            }
        }
    }
    Flow {
        Layout.fillWidth: true; Layout.preferredHeight: implicitHeight; spacing: 4
        ActionButton { text: "A−"; onClicked: panel.editor.setSize(panel.editor.textSize-2) }
        Label { text: "Text "+panel.editor.textSize; height: 30; verticalAlignment: Text.AlignVCenter }
        ActionButton { text: "A+"; onClicked: panel.editor.setSize(panel.editor.textSize+2) }
    }
    Flow {
        Layout.fillWidth: true; Layout.preferredHeight: implicitHeight; spacing: 4
        ActionButton { text: "Thin −"; onClicked: panel.editor.setWeight(studio.renderSettings.lineWt-.2) }
        Label { text: studio.renderSettings.lineWt.toFixed(1)+"×"; height: 30; verticalAlignment: Text.AlignVCenter }
        ActionButton { text: "Thick +"; onClicked: panel.editor.setWeight(studio.renderSettings.lineWt+.2) }
    }
    Text { text: "SELECTED MARKUP"; color: "#9DAFC2"; font.pixelSize: 11 }
    ComboBox {
        objectName: "markupSelection"
        Layout.fillWidth: true; model: panel.editor.rows; textRole: "label"
        currentIndex: panel.editor.selection
        displayText: currentIndex<0 ? "Choose a drawing…" : currentText
        onActivated: panel.editor.select(currentIndex)
    }
    ActionButton { text: "Deselect / new defaults"; enabled: panel.editor.selection>=0; onClicked: panel.editor.select(-1) }
    ColumnLayout {
        Layout.fillWidth: true; enabled: panel.editor.selection>=0
        Flow {
            Layout.fillWidth: true; Layout.preferredHeight: implicitHeight; spacing: 4
            ActionButton { text: "Edit text"; enabled: panel.editor.selected.tool==="text"; onClicked: panel.editor.editText() }
            ActionButton { objectName: "markupDuplicate"; text: "Duplicate"; onClicked: panel.editor.duplicate() }
            ActionButton { objectName: "markupDelete"; text: "Delete mark"; onClicked: panel.editor.delete() }
        }
        Text { text: "Move selected mark"; color: "#9DAFC2"; font.pixelSize: 11 }
        Flow {
            Layout.fillWidth: true; Layout.preferredHeight: implicitHeight; spacing: 4
            ActionButton { text: "Left"; onClicked: panel.editor.move(-.01,0) }
            ActionButton { text: "Up"; onClicked: panel.editor.move(0,-.01) }
            ActionButton { text: "Down"; onClicked: panel.editor.move(0,.01) }
            ActionButton { text: "Right"; onClicked: panel.editor.move(.01,0) }
        }
        MarkupTimingPanel { Layout.fillWidth: true; editor: panel.editor }
    }
    Text { text: "Zone: drag a rectangle. Ring: drag from its centre. Pen: draw freely. Escape cancels a stroke."; color: "#9DAFC2"; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
}
