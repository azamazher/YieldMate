// ============================================================================
// DETECTION SERVICE - Post-processing, NMS, IoU calculations
// ============================================================================
import 'dart:math' as math;
import 'package:flutter/material.dart';

class DetectionService {
  /// Process model output and return detections
  static List<Map<String, dynamic>> processOutput(
      List<List<List<double>>> output, List<String> labels,
      {double confThreshold = 0.5, double iouThreshold = 0.5}) {
    final List<Rect> bboxes = [];
    final List<double> scores = [];
    final List<int> classIndices = [];

    // Validate output dimensions
    if (output.isEmpty || output[0].isEmpty) {
      print("⚠️ Empty output from model");
      return [];
    }

    print(
        "📊 Output dimensions: ${output.length} x ${output[0].length} x ${output[0][0].length}");

    // Check if output format matches YOLO detection format
    final firstDim = output[0].length;
    final secondDim = output[0][0].length;

    print("📊 First dimension: $firstDim, Second dimension: $secondDim");
    print(
        "📊 Expected: 12 (8 classes + 4 bbox) or 8400+ detections for 8 classes");

    // Determine output format and transpose accordingly
    List<List<double>> transposedOutput;

    if (firstDim >= 7 && secondDim >= 100) {
      // Format: [1, 7, num_detections] - YOLO format
      print("📊 Detected format: [batch, classes+4, detections]");
      transposedOutput = List.generate(
          secondDim, (i) => List.generate(firstDim, (j) => output[0][j][i]));
    } else if (secondDim >= 7 && firstDim >= 100) {
      // Format: [1, num_detections, 7] - Already transposed
      print("📊 Detected format: [batch, detections, classes+4]");
      transposedOutput = output[0];
    } else {
      print(
          "⚠️ Unexpected output dimensions. First: $firstDim, Second: $secondDim");
      print("⚠️ This might be a classification model, not object detection");
      throw Exception(
          "Model output format doesn't match object detection format. "
          "Expected YOLO format [1, 7, N] or [1, N, 7], got [1, $firstDim, $secondDim]. "
          "This model might be a classification model, not object detection.");
    }

    print("📊 Processing ${transposedOutput.length} detections");
    print(
        "📊 Confidence threshold: $confThreshold, IoU threshold: $iouThreshold");
    print("📊 Looking for ${labels.length} classes: ${labels.join(', ')}");

    int processedCount = 0;
    int filteredCount = 0;

    for (final det in transposedOutput) {
      processedCount++;
      // Validate detection array has enough elements
      if (det.length < 7) {
        continue;
      }

      // YOLOv8 TFLite format: [cx, cy, w, h, class1_logit, class2_logit, ..., class8_logit]
      final cx = det[0];
      final cy = det[1];
      final w = det[2];
      final h = det[3];

      // Handle different YOLOv8 output formats
      double confidence;
      int classProbStartIndex;

      if (det.length >= 5 + labels.length) {
        // Standard format: confidence at index 4, classes start at 5
        final confValue = det[4];
        if (confValue < 0 || confValue > 1) {
          confidence = 1.0 / (1.0 + math.exp(-confValue));
        } else {
          confidence = confValue.clamp(0.0, 1.0);
        }
        classProbStartIndex = 5;
      } else if (det.length >= 4 + labels.length) {
        // YOLOv8 TFLite format: no separate confidence, classes start at 4
        classProbStartIndex = 4;
        confidence = 1.0; // Will be set to max class prob below
      } else {
        continue;
      }

      // Find class with highest probability
      // Pre-filter by raw logit value BEFORE applying sigmoid
      double maxRawLogit = double.negativeInfinity;
      for (int i = classProbStartIndex;
          i < det.length && i < classProbStartIndex + labels.length;
          i++) {
        if (det[i] > maxRawLogit) {
          maxRawLogit = det[i];
        }
      }

      // DEBUG: Log first 10 detections
      if (processedCount <= 10) {
        print(
            "   Detection $processedCount: maxRawLogit=$maxRawLogit, sigmoid($maxRawLogit)=${1.0 / (1.0 + math.exp(-maxRawLogit.clamp(-20.0, 20.0)))}");
      }

      // Filter noise BEFORE applying sigmoid
      if (maxRawLogit < 0.3) {
        continue; // Skip noise detections
      }

      // Apply sigmoid to convert logits to probabilities
      double maxProb = 0.0;
      int classIndex = 0;

      for (int i = classProbStartIndex;
          i < det.length && i < classProbStartIndex + labels.length;
          i++) {
        final logit = det[i];
        final clampedLogit = logit.clamp(-20.0, 20.0);
        final prob = 1.0 / (1.0 + math.exp(-clampedLogit));

        if (prob > maxProb) {
          maxProb = prob;
          classIndex = i - classProbStartIndex;
        }
      }

      // If no separate confidence score, use max class probability as confidence
      if (classProbStartIndex == 4) {
        confidence = maxProb;
      }

      final score = confidence;

      if (processedCount <= 5 && score >= confThreshold) {
        print(
            "   ✅ Valid detection $processedCount: class=${labels[classIndex]}, score=$score, maxProb=$maxProb");
      }

      if (score < confThreshold) {
        filteredCount++;
        continue;
      }

      // Validate class index
      if (classIndex >= labels.length) {
        continue;
      }

      // Validate bbox coordinates
      if (w <= 0 ||
          h <= 0 ||
          cx < 0 ||
          cy < 0 ||
          cx.isNaN ||
          cy.isNaN ||
          w.isNaN ||
          h.isNaN ||
          cx.isInfinite ||
          cy.isInfinite ||
          w.isInfinite ||
          h.isInfinite) {
        continue;
      }

      // Convert xywh to xyxy
      final left = cx - w / 2;
      final top = cy - h / 2;
      final right = cx + w / 2;
      final bottom = cy + h / 2;

      if (right <= left || bottom <= top) {
        continue;
      }

      // Clamp to [0, 1] range
      final clampedLeft = left.clamp(0.0, 1.0);
      final clampedTop = top.clamp(0.0, 1.0);
      final clampedRight = right.clamp(0.0, 1.0);
      final clampedBottom = bottom.clamp(0.0, 1.0);

      if (clampedRight <= clampedLeft || clampedBottom <= clampedTop) {
        continue;
      }

      // Store normalized coordinates
      bboxes.add(
          Rect.fromLTRB(clampedLeft, clampedTop, clampedRight, clampedBottom));
      scores.add(score);
      classIndices.add(classIndex);
    }

    print(
        "📊 Detections before NMS: ${bboxes.length} (processed: $processedCount, filtered: $filteredCount)");

    final nmsIndices = nonMaxSuppression(bboxes, scores, iouThreshold);

    print("📊 Detections after NMS: ${nmsIndices.length}");

    final results = <Map<String, dynamic>>[];
    for (final index in nmsIndices) {
      results.add({
        'rect': bboxes[index],
        'detectedClass': labels[classIndices[index]],
        'confidenceInClass': scores[index],
      });
    }

    return results;
  }

  /// Non-Maximum Suppression - Removes duplicate detections
  static List<int> nonMaxSuppression(
      List<Rect> boxes, List<double> scores, double iouThreshold) {
    if (boxes.isEmpty) return [];
    final indices = List.generate(boxes.length, (i) => i);
    indices.sort((a, b) => scores[b].compareTo(scores[a]));
    final keep = <int>[];

    while (indices.isNotEmpty) {
      final i = indices.removeAt(0);
      keep.add(i);
      final suppressed = <int>[];
      for (int j = 0; j < indices.length; j++) {
        final idx = indices[j];
        final iou = calculateIoU(boxes[i], boxes[idx]);
        if (iou > iouThreshold) suppressed.add(idx);
      }
      indices.removeWhere((idx) => suppressed.contains(idx));
    }
    return keep;
  }

  /// Intersection over Union (IoU) calculation for NMS
  static double calculateIoU(Rect a, Rect b) {
    // Calculate intersection rectangle
    final double interLeft = math.max(a.left, b.left);
    final double interTop = math.max(a.top, b.top);
    final double interRight = math.min(a.right, b.right);
    final double interBottom = math.min(a.bottom, b.bottom);

    // If no intersection, return 0
    if (interRight <= interLeft || interBottom <= interTop) {
      return 0.0;
    }

    // Calculate intersection area
    final double interArea =
        (interRight - interLeft) * (interBottom - interTop);

    // Calculate union area
    final double boxAArea = a.width * a.height;
    final double boxBArea = b.width * b.height;
    final double unionArea = boxAArea + boxBArea - interArea;

    // Avoid division by zero
    if (unionArea <= 0) return 0.0;

    // Return IoU
    return interArea / unionArea;
  }
}

