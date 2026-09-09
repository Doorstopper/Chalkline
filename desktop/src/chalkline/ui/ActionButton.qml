import QtQuick.Controls

// Shared sizing for the dense transport, tag and project action bars.
Button {
    implicitWidth: Math.max(32, implicitContentWidth + leftPadding + rightPadding)
    implicitHeight: 30
    leftPadding: 9
    rightPadding: 9
}
