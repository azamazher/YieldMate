// ============================================================================
// BOUNDING BOX PAINTER - Draws detection boxes on images
// ============================================================================
import 'package:flutter/material.dart';
import 'dart:ui' as ui;

class BoundingBoxPainter extends CustomPainter {
  final List<Map<String, dynamic>> recognitions;
  final Map<String, Color> fruitColors;
  final double imageWidth;
  final double imageHeight;

  BoundingBoxPainter({
    required this.recognitions,
    required this.fruitColors,
    required this.imageWidth,
    required this.imageHeight,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (recognitions.isEmpty || imageWidth <= 0 || imageHeight <= 0) return;

    // Calculate scale factors to map from image coordinates to displayed size
    final scaleX = size.width / imageWidth;
    final scaleY = size.height / imageHeight;

    for (final recognition in recognitions) {
      final rect = recognition['rect'] as Rect;
      final detectedClass = recognition['detectedClass'] as String;
      final confidence = recognition['confidenceInClass'] as double;

      // Scale bounding box to displayed size
      final scaledRect = Rect.fromLTRB(
        rect.left * scaleX,
        rect.top * scaleY,
        rect.right * scaleX,
        rect.bottom * scaleY,
      );

      // Get color for this fruit
      final color = fruitColors[detectedClass.toLowerCase()] ??
          fruitColors['default']!;

      // Draw bounding box
      final boxPaint = Paint()
        ..color = color
        ..style = PaintingStyle.stroke
        ..strokeWidth = 3.0;

      canvas.drawRect(scaledRect, boxPaint);

      // Draw label background
      final textSpan = TextSpan(
        text: '${detectedClass.toUpperCase()} ${(confidence * 100).toStringAsFixed(0)}%',
        style: TextStyle(
          color: Colors.white,
          fontSize: 12,
          fontWeight: FontWeight.bold,
        ),
      );

      final textPainter = TextPainter(
        text: textSpan,
        textDirection: ui.TextDirection.ltr,
      );
      textPainter.layout();

      final labelRect = Rect.fromLTWH(
        scaledRect.left,
        scaledRect.top - textPainter.height - 4,
        textPainter.width + 8,
        textPainter.height + 4,
      );

      final labelPaint = Paint()..color = color;
      canvas.drawRect(labelRect, labelPaint);

      // Draw label text
      textPainter.paint(
        canvas,
        Offset(scaledRect.left + 4, scaledRect.top - textPainter.height),
      );
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

