// ============================================================================
// PITCHFORK ICON PAINTER - Custom drawn icon
// ============================================================================
import 'package:flutter/material.dart';

class PitchforkIconPainter extends CustomPainter {
  final Color color;

  PitchforkIconPainter({required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3.0
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;

    final centerX = size.width / 2;
    final centerY = size.height / 2;

    // Handle (vertical line)
    final handleTopY = centerY - 15;
    final handleBottomY = centerY + 15;
    canvas.drawLine(
      Offset(centerX, handleTopY),
      Offset(centerX, handleBottomY),
      paint,
    );

    // Base (horizontal line connecting to tines)
    final tineBaseX = centerX - 8;
    final tineBaseY = centerY - 5;
    final tineLength = 22.0;
    final tineSpacing = 7.0;

    for (int i = 0; i < 3; i++) {
      final tineX = tineBaseX + (i * tineSpacing);
      final tineY = tineBaseY - (i * 1.5); // Slight vertical offset

      // Tine shaft (diagonal)
      final tineEndX = tineX + (tineLength * 0.3);
      final tineEndY = tineY - (tineLength * 0.95);

      canvas.drawLine(
        Offset(tineX, tineY),
        Offset(tineEndX, tineEndY),
        paint,
      );

      // Tine point (curved upward)
      final pointPath = Path()
        ..moveTo(tineEndX, tineEndY)
        ..quadraticBezierTo(
          tineEndX + 2,
          tineEndY - 1,
          tineEndX + 4,
          tineEndY - 4,
        );
      canvas.drawPath(pointPath, paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

