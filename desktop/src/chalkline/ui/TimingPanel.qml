import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    spacing: 8
    CheckBox {
        text: "Auto-freeze at drawings"
        checked: studio.renderSettings.autoFreeze
        onClicked: studio.setFreezeSettings(checked,studio.renderSettings.hold,studio.renderSettings.burnAll)
    }
    RowLayout {
        Label { text: "Global hold (s)" }
        TextField {
            Layout.fillWidth: true; text: studio.renderSettings.hold
            validator: DoubleValidator { bottom: 0; top: 30 }
            onEditingFinished: studio.setFreezeSettings(studio.renderSettings.autoFreeze,Number(text),studio.renderSettings.burnAll)
        }
    }
    CheckBox {
        text: "Show drawings for whole clip"
        checked: studio.renderSettings.burnAll
        onClicked: studio.setFreezeSettings(studio.renderSettings.autoFreeze,studio.renderSettings.hold,checked)
    }
    Button { text: "Freeze here…"; Layout.fillWidth: true; enabled: studio.selection>=0 && !studio.busy; onClicked: studio.addFreeze() }
    Repeater {
        model: studio.freezeRows
        ColumnLayout {
            required property var modelData
            required property int index
            Layout.fillWidth: true
            Label { text: "Freeze at "+modelData.at.toFixed(1)+"s · hold "+modelData.hold+"s"; font.pixelSize: 11 }
            RowLayout {
                Button { text: "Go"; onClicked: { studio.seek(modelData.at); if(studio.playing) studio.togglePlay() } }
                Button { text: "Edit"; enabled: !studio.busy; onClicked: studio.editTiming("freezes",index) }
                Button { text: "Delete"; enabled: !studio.busy; onClicked: studio.deleteTiming("freezes",index) }
            }
        }
    }
    Label { text: "SLOW SECTIONS"; font.pixelSize: 11; color: "#9DAFC2" }
    RowLayout {
        Button { text: "Slow from"; enabled: studio.selection>=0; onClicked: studio.slowFrom() }
        Button { text: "To here"; enabled: studio.slowPending>=0 && !studio.busy; onClicked: studio.slowTo() }
    }
    Button {
        visible: studio.slowPending>=0; Layout.fillWidth: true
        text: "Cancel start at "+studio.slowPending.toFixed(1)+"s"; onClicked: studio.cancelSlow()
    }
    Button { text: "Add slow section…"; Layout.fillWidth: true; enabled: studio.selection>=0 && !studio.busy; onClicked: studio.addSlow() }
    Repeater {
        model: studio.slowRows
        ColumnLayout {
            required property var modelData
            required property int index
            Layout.fillWidth: true
            Label { text: modelData.from.toFixed(1)+"–"+modelData.to.toFixed(1)+"s · "+modelData.rate+"×"; font.pixelSize: 11 }
            RowLayout {
                Button { text: "Go"; onClicked: { studio.seek(modelData.from); if(studio.playing) studio.togglePlay() } }
                Button { text: "Edit"; enabled: !studio.busy; onClicked: studio.editTiming("slow",index) }
                Button { text: "Delete"; enabled: !studio.busy; onClicked: studio.deleteTiming("slow",index) }
            }
        }
    }
}
