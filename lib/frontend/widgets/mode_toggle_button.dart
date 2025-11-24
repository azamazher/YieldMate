// ============================================================================
// MODE TOGGLE BUTTON - Offline/Online mode switcher
// ============================================================================
import 'package:flutter/material.dart';

class ModeToggleButton extends StatelessWidget {
  final bool isOnlineMode;
  final bool canUseOnline;
  final VoidCallback onTap;

  const ModeToggleButton({
    super.key,
    required this.isOnlineMode,
    required this.canUseOnline,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: isOnlineMode
          ? (canUseOnline
              ? 'Online Mode (Backend)'
              : 'Online Mode (No Internet)')
          : 'Offline Mode (TFLite)',
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(20),
            gradient: LinearGradient(
              colors: isOnlineMode
                  ? [
                      Colors.blue.withOpacity(0.2),
                      Colors.blue.withOpacity(0.1),
                    ]
                  : [
                      Colors.green.withOpacity(0.2),
                      Colors.green.withOpacity(0.1),
                    ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            border: Border.all(
              color: isOnlineMode
                  ? (canUseOnline
                      ? Colors.blue.withOpacity(0.5)
                      : Colors.grey.withOpacity(0.3))
                  : Colors.green.withOpacity(0.5),
              width: 1.5,
            ),
            boxShadow: [
              BoxShadow(
                color: (isOnlineMode ? Colors.blue : Colors.green)
                    .withOpacity(0.1),
                blurRadius: 8,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                isOnlineMode ? Icons.cloud : Icons.phone_android,
                size: 18,
                color: isOnlineMode
                    ? (canUseOnline ? Colors.blue : Colors.grey)
                    : Colors.green,
              ),
              const SizedBox(width: 6),
              Text(
                isOnlineMode ? 'Online' : 'Offline',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: isOnlineMode
                      ? (canUseOnline ? Colors.blue : Colors.grey)
                      : Colors.green,
                ),
              ),
              if (isOnlineMode && !canUseOnline)
                Padding(
                  padding: const EdgeInsets.only(left: 4),
                  child: Icon(
                    Icons.wifi_off,
                    size: 14,
                    color: Colors.red,
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

