// ============================================================================
// APP DRAWER - MODERN MENU NAVIGATION
// ============================================================================
import 'package:flutter/material.dart';

class AppDrawer extends StatefulWidget {
  final String currentRoute;

  const AppDrawer({
    super.key,
    required this.currentRoute,
  });

  @override
  State<AppDrawer> createState() => _AppDrawerState();
}

class _AppDrawerState extends State<AppDrawer> with TickerProviderStateMixin {
  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;

  // Drawer opening animation
  late AnimationController _drawerAnimationController;
  late Animation<double> _headerSlideAnimation;
  late Animation<double> _headerFadeAnimation;
  late Animation<double> _headerScaleAnimation;

  @override
  void initState() {
    super.initState();
    // Pulse animation for the green dot
    _pulseController = AnimationController(
      duration: const Duration(milliseconds: 1500),
      vsync: this,
    )..repeat(reverse: true);

    _pulseAnimation = Tween<double>(begin: 0.6, end: 1.0).animate(
      CurvedAnimation(
        parent: _pulseController,
        curve: Curves.easeInOut,
      ),
    );

    // Drawer opening animation
    _drawerAnimationController = AnimationController(
      duration: const Duration(milliseconds: 600),
      vsync: this,
    );

    // Header slide animation (from left)
    _headerSlideAnimation = Tween<double>(begin: -50.0, end: 0.0).animate(
      CurvedAnimation(
        parent: _drawerAnimationController,
        curve: const Interval(0.0, 0.5, curve: Curves.easeOutCubic),
      ),
    );

    // Header fade animation
    _headerFadeAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _drawerAnimationController,
        curve: const Interval(0.0, 0.5, curve: Curves.easeOut),
      ),
    );

    // Header scale animation
    _headerScaleAnimation = Tween<double>(begin: 0.8, end: 1.0).animate(
      CurvedAnimation(
        parent: _drawerAnimationController,
        curve: const Interval(0.0, 0.5, curve: Curves.easeOutBack),
      ),
    );

    // Start the animation when drawer opens
    _drawerAnimationController.forward();
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _drawerAnimationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Drawer(
      backgroundColor: isDark ? const Color(0xFF1A1A1A) : Colors.white,
      child: Column(
        children: [
          // Modern Creative Gradient Header with animation
          AnimatedBuilder(
            animation: _drawerAnimationController,
            builder: (context, child) {
              return Transform.translate(
                offset: Offset(_headerSlideAnimation.value, 0),
                child: Transform.scale(
                  scale: _headerScaleAnimation.value,
                  child: Opacity(
                    opacity: _headerFadeAnimation.value,
                    child: Container(
                      constraints:
                          const BoxConstraints(minHeight: 180, maxHeight: 200),
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                          colors: [
                            Color(0xFF6366F1), // Indigo
                            Color(0xFF8B5CF6), // Purple
                            Color(0xFFEC4899), // Pink
                          ],
                        ),
                        boxShadow: [
                          BoxShadow(
                            color: const Color(0xFF8B5CF6).withOpacity(0.4),
                            blurRadius: 15,
                            offset: const Offset(0, 5),
                            spreadRadius: 2,
                          ),
                        ],
                      ),
                      child: Stack(
                        children: [
                          // Animated gradient overlay for depth
                          Positioned.fill(
                            child: Container(
                              decoration: BoxDecoration(
                                gradient: LinearGradient(
                                  begin: Alignment.topRight,
                                  end: Alignment.bottomLeft,
                                  colors: [
                                    Colors.white.withOpacity(0.1),
                                    Colors.transparent,
                                    Colors.black.withOpacity(0.1),
                                  ],
                                ),
                              ),
                            ),
                          ),
                          // Geometric pattern
                          Positioned.fill(
                            child: Opacity(
                              opacity: 0.1,
                              child: CustomPaint(
                                painter: _GeometricPatternPainter(),
                              ),
                            ),
                          ),
                          // Content
                          SafeArea(
                            child: Padding(
                              padding:
                                  const EdgeInsets.fromLTRB(24, 40, 24, 18),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                mainAxisAlignment: MainAxisAlignment.start,
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  // Creative YieldMate Text with unique styling
                                  Row(
                                    crossAxisAlignment: CrossAxisAlignment.end,
                                    children: [
                                      // First letter without accent dot
                                      Text(
                                        'Y',
                                        style: TextStyle(
                                          fontSize: 42,
                                          fontWeight: FontWeight.w900,
                                          height: 0.9,
                                          foreground: Paint()
                                            ..shader = const LinearGradient(
                                              colors: [
                                                Colors.white,
                                                Color(0xFFFFF9C4),
                                              ],
                                            ).createShader(
                                              const Rect.fromLTWH(0, 0, 50, 50),
                                            ),
                                          shadows: [
                                            Shadow(
                                              color:
                                                  Colors.black.withOpacity(0.4),
                                              offset: const Offset(2, 3),
                                              blurRadius: 6,
                                            ),
                                            Shadow(
                                              color: const Color(0xFFEC4899)
                                                  .withOpacity(0.5),
                                              offset: const Offset(-1, -1),
                                              blurRadius: 4,
                                            ),
                                          ],
                                        ),
                                      ),
                                      // Rest of the text
                                      ShaderMask(
                                        shaderCallback: (bounds) =>
                                            const LinearGradient(
                                          colors: [
                                            Colors.white,
                                            Color(0xFFE0E7FF),
                                            Colors.white,
                                          ],
                                          begin: Alignment.topLeft,
                                          end: Alignment.bottomRight,
                                        ).createShader(bounds),
                                        child: Text(
                                          'ieldMate',
                                          style: TextStyle(
                                            fontSize: 38,
                                            fontWeight: FontWeight.w800,
                                            letterSpacing: 0.8,
                                            height: 0.9,
                                            color: Colors.white,
                                            shadows: [
                                              Shadow(
                                                color: Colors.black
                                                    .withOpacity(0.3),
                                                offset: const Offset(1, 2),
                                                blurRadius: 4,
                                              ),
                                            ],
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 8),
                                  // Creative subtitle badge with pulsing green dot
                                  Container(
                                    padding: const EdgeInsets.symmetric(
                                        horizontal: 12, vertical: 6),
                                    decoration: BoxDecoration(
                                      gradient: LinearGradient(
                                        colors: [
                                          Colors.white.withOpacity(0.25),
                                          Colors.white.withOpacity(0.15),
                                        ],
                                      ),
                                      borderRadius: BorderRadius.circular(25),
                                      border: Border.all(
                                        color: Colors.white.withOpacity(0.4),
                                        width: 1.5,
                                      ),
                                      boxShadow: [
                                        BoxShadow(
                                          color: Colors.black.withOpacity(0.2),
                                          blurRadius: 8,
                                          offset: const Offset(0, 2),
                                        ),
                                      ],
                                    ),
                                    child: Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        // Pulsing green dot
                                        AnimatedBuilder(
                                          animation: _pulseAnimation,
                                          builder: (context, child) {
                                            return Container(
                                              width: 6,
                                              height: 6,
                                              decoration: BoxDecoration(
                                                color: Colors.green,
                                                shape: BoxShape.circle,
                                                boxShadow: [
                                                  BoxShadow(
                                                    color: Colors.green
                                                        .withOpacity(
                                                      0.8 *
                                                          _pulseAnimation.value,
                                                    ),
                                                    blurRadius: 6 *
                                                        _pulseAnimation.value,
                                                    spreadRadius: 2 *
                                                        _pulseAnimation.value,
                                                  ),
                                                ],
                                              ),
                                            );
                                          },
                                        ),
                                        const SizedBox(width: 8),
                                        Text(
                                          'Smart Fruit Detection',
                                          style: TextStyle(
                                            color: Colors.white,
                                            fontSize: 12,
                                            fontWeight: FontWeight.w700,
                                            letterSpacing: 0.8,
                                            height: 1.2,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              );
            },
          ),

          // Menu Items with staggered animation
          Expanded(
            child: AnimatedBuilder(
              animation: _drawerAnimationController,
              builder: (context, child) {
                return ListView(
                  padding:
                      const EdgeInsets.symmetric(vertical: 16, horizontal: 12),
                  children: [
                    // Home Menu Item
                    _buildAnimatedMenuItem(
                      context: context,
                      icon: Icons.home_rounded,
                      title: 'Home',
                      subtitle: 'Main detection',
                      route: '/home',
                      isSelected: widget.currentRoute == '/home',
                      isLocked: false,
                      gradient: const LinearGradient(
                        colors: [Color(0xFF4CAF50), Color(0xFF45A049)],
                      ),
                      animationController: _drawerAnimationController,
                      delay: 0.5,
                      index: 0,
                    ),

                    const SizedBox(height: 8),

                    // Calendar Menu Item
                    _buildAnimatedMenuItem(
                      context: context,
                      icon: Icons.calendar_today_rounded,
                      title: 'Calendar',
                      subtitle: 'Detection history',
                      route: '/calendar',
                      isSelected: widget.currentRoute == '/calendar',
                      isLocked: false,
                      gradient: const LinearGradient(
                        colors: [Color(0xFF2196F3), Color(0xFF1976D2)],
                      ),
                      animationController: _drawerAnimationController,
                      delay: 0.5,
                      index: 1,
                    ),

                    const SizedBox(height: 8),

                    // Live Detection Menu Item
                    _buildAnimatedMenuItem(
                      context: context,
                      icon: Icons.videocam_rounded,
                      title: 'Live Detection',
                      subtitle: 'Real-time fruit detection',
                      route: '/live-detection',
                      isSelected: widget.currentRoute == '/live-detection',
                      isLocked: false,
                      gradient: const LinearGradient(
                        colors: [
                          Color(0xFF1E3A8A),
                          Color(0xFF7E22CE),
                          Color(0xFFDB2777),
                        ],
                      ),
                      animationController: _drawerAnimationController,
                      delay: 0.5,
                      index: 2,
                    ),

                    const SizedBox(height: 24),

                    // Section Label
                    _buildAnimatedSectionLabel(
                      'Coming Soon',
                      _drawerAnimationController,
                      delay: 0.5,
                      index: 3,
                    ),

                    const SizedBox(height: 8),

                    // Fruit Doctor Menu Item (Locked)
                    _buildAnimatedMenuItem(
                      context: context,
                      icon: Icons.medical_services_rounded,
                      title: 'Fruit Doctor',
                      subtitle: 'Health insights',
                      route: '/fruit-doctor',
                      isSelected: widget.currentRoute == '/fruit-doctor',
                      isLocked: true,
                      gradient: LinearGradient(
                        colors: [
                          Colors.grey[400]!,
                          Colors.grey[500]!,
                        ],
                      ),
                      animationController: _drawerAnimationController,
                      delay: 0.5,
                      index: 4,
                    ),

                    const SizedBox(height: 8),

                    // Community Menu Item (Locked)
                    _buildAnimatedMenuItem(
                      context: context,
                      icon: Icons.people_rounded,
                      title: 'Community',
                      subtitle: 'Share & learn',
                      route: '/community',
                      isSelected: widget.currentRoute == '/community',
                      isLocked: true,
                      gradient: LinearGradient(
                        colors: [
                          Colors.grey[400]!,
                          Colors.grey[500]!,
                        ],
                      ),
                      animationController: _drawerAnimationController,
                      delay: 0.5,
                      index: 5,
                    ),

                    const SizedBox(height: 24),

                    // About Menu Item
                    _buildAnimatedMenuItem(
                      context: context,
                      icon: Icons.info_rounded,
                      title: 'About',
                      subtitle: 'App information',
                      route: '/about',
                      isSelected: widget.currentRoute == '/about',
                      isLocked: false,
                      gradient: const LinearGradient(
                        colors: [Color(0xFF9E9E9E), Color(0xFF757575)],
                      ),
                      animationController: _drawerAnimationController,
                      delay: 0.5,
                      index: 6,
                    ),

                    const SizedBox(height: 20),
                  ],
                );
              },
            ),
          ),

          // Footer with animation
          AnimatedBuilder(
            animation: _drawerAnimationController,
            builder: (context, child) {
              final footerAnimation =
                  Tween<double>(begin: 0.0, end: 1.0).animate(
                CurvedAnimation(
                  parent: _drawerAnimationController,
                  curve: const Interval(0.8, 1.0, curve: Curves.easeOut),
                ),
              );

              return Transform.translate(
                offset: Offset(0, 30 * (1 - footerAnimation.value)),
                child: Opacity(
                  opacity: footerAnimation.value,
                  child: Container(
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(
                      border: Border(
                        top: BorderSide(
                          color: isDark ? Colors.grey[800]! : Colors.grey[200]!,
                          width: 1,
                        ),
                      ),
                    ),
                    child: Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: isDark ? Colors.grey[800] : Colors.grey[100],
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Icon(
                            Icons.code_rounded,
                            size: 20,
                            color: isDark ? Colors.grey[400] : Colors.grey[600],
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Version 1.0.0',
                                style: TextStyle(
                                  fontSize: 12,
                                  fontWeight: FontWeight.w600,
                                  color: isDark
                                      ? Colors.grey[300]
                                      : Colors.grey[700],
                                ),
                              ),
                              Text(
                                'Made with ❤️',
                                style: TextStyle(
                                  fontSize: 10,
                                  color: isDark
                                      ? Colors.grey[500]
                                      : Colors.grey[500],
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              );
            },
          ),
        ],
      ),
    );
  }

  // Animated menu item with staggered fade-in
  Widget _buildAnimatedMenuItem({
    required BuildContext context,
    required IconData icon,
    required String title,
    required String subtitle,
    required String route,
    required bool isSelected,
    required bool isLocked,
    required Gradient gradient,
    required AnimationController animationController,
    required double delay,
    required int index,
  }) {
    // Calculate animation for this item
    final itemDelay = delay + (index * 0.1);
    final itemAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: animationController,
        curve: Interval(
          itemDelay.clamp(0.0, 1.0),
          (itemDelay + 0.3).clamp(0.0, 1.0),
          curve: Curves.easeOut,
        ),
      ),
    );

    return AnimatedBuilder(
      animation: itemAnimation,
      builder: (context, child) {
        return Transform.translate(
          offset: Offset(30 * (1 - itemAnimation.value), 0),
          child: Opacity(
            opacity: itemAnimation.value,
            child: _buildModernMenuItem(
              context: context,
              icon: icon,
              title: title,
              subtitle: subtitle,
              route: route,
              isSelected: isSelected,
              isLocked: isLocked,
              gradient: gradient,
            ),
          ),
        );
      },
    );
  }

  // Animated section label
  Widget _buildAnimatedSectionLabel(
    String text,
    AnimationController animationController, {
    required double delay,
    required int index,
  }) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final itemDelay = delay + (index * 0.1);
    final itemAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: animationController,
        curve: Interval(
          itemDelay.clamp(0.0, 1.0),
          (itemDelay + 0.3).clamp(0.0, 1.0),
          curve: Curves.easeOut,
        ),
      ),
    );

    return AnimatedBuilder(
      animation: itemAnimation,
      builder: (context, child) {
        return Transform.translate(
          offset: Offset(30 * (1 - itemAnimation.value), 0),
          child: Opacity(
            opacity: itemAnimation.value,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              child: Text(
                text,
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: isDark ? Colors.grey[500] : Colors.grey[600],
                  letterSpacing: 1.2,
                ),
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _buildModernMenuItem({
    required BuildContext context,
    required IconData icon,
    required String title,
    required String subtitle,
    required String route,
    required bool isSelected,
    required bool isLocked,
    required Gradient gradient,
  }) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: isLocked
            ? () {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Row(
                      children: [
                        Icon(
                          Icons.lock_rounded,
                          color: Colors.white,
                          size: 20,
                        ),
                        const SizedBox(width: 8),
                        Text('$title is coming soon!'),
                      ],
                    ),
                    behavior: SnackBarBehavior.floating,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(10),
                    ),
                    duration: const Duration(seconds: 2),
                  ),
                );
              }
            : () {
                Navigator.pop(context);
                if (route != widget.currentRoute) {
                  Navigator.pushNamed(context, route);
                }
              },
        borderRadius: BorderRadius.circular(16),
        child: Container(
          margin: const EdgeInsets.symmetric(horizontal: 8),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: isSelected
                ? (isDark
                    ? Colors.green.withOpacity(0.2)
                    : Colors.green.withOpacity(0.1))
                : (isDark ? Colors.grey[850] : Colors.grey[50]),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: isSelected
                  ? Colors.green.withOpacity(0.5)
                  : (isDark ? Colors.grey[700]! : Colors.grey[200]!),
              width: isSelected ? 2 : 1,
            ),
            boxShadow: isSelected
                ? [
                    BoxShadow(
                      color: Colors.green.withOpacity(0.2),
                      blurRadius: 8,
                      offset: const Offset(0, 2),
                    ),
                  ]
                : null,
          ),
          child: Row(
            children: [
              // Icon Container
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  gradient: isLocked
                      ? LinearGradient(
                          colors: [
                            Colors.grey[400]!,
                            Colors.grey[500]!,
                          ],
                        )
                      : gradient,
                  borderRadius: BorderRadius.circular(12),
                  boxShadow: [
                    BoxShadow(
                      color: (isLocked ? Colors.grey[400]! : gradient.colors[0])
                          .withOpacity(0.3),
                      blurRadius: 8,
                      offset: const Offset(0, 2),
                    ),
                  ],
                ),
                child: Icon(
                  icon,
                  color: Colors.white,
                  size: 24,
                ),
              ),
              const SizedBox(width: 16),
              // Text Content
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Text(
                          title,
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight:
                                isSelected ? FontWeight.bold : FontWeight.w600,
                            color: isLocked
                                ? Colors.grey
                                : (isDark ? Colors.white : Colors.black87),
                          ),
                        ),
                        if (isLocked) ...[
                          const SizedBox(width: 8),
                          Icon(
                            Icons.lock_rounded,
                            size: 14,
                            color: Colors.grey[500],
                          ),
                        ],
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      subtitle,
                      style: TextStyle(
                        fontSize: 12,
                        color: isLocked
                            ? Colors.grey[500]
                            : (isDark ? Colors.grey[400] : Colors.grey[600]),
                      ),
                    ),
                  ],
                ),
              ),
              // Arrow Indicator
              if (!isLocked)
                Icon(
                  Icons.chevron_right_rounded,
                  color: isSelected
                      ? Colors.green
                      : (isDark ? Colors.grey[600] : Colors.grey[400]),
                  size: 24,
                ),
            ],
          ),
        ),
      ),
    );
  }
}

// Geometric Pattern Painter for header background
class _GeometricPatternPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.white
      ..style = PaintingStyle.fill;

    // Draw geometric shapes pattern
    // Draw hexagons/circles pattern
    for (int i = 0; i < 6; i++) {
      for (int j = 0; j < 3; j++) {
        final x = size.width * 0.15 * (i + 1);
        final y = size.height * 0.25 * (j + 1);

        // Draw circles with varying sizes
        canvas.drawCircle(
          Offset(x, y),
          20 + (i % 3) * 5,
          paint..color = Colors.white.withOpacity(0.15),
        );
      }
    }

    // Draw diagonal lines
    final linePaint = Paint()
      ..color = Colors.white.withOpacity(0.1)
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke;

    for (int i = 0; i < 5; i++) {
      canvas.drawLine(
        Offset(0, size.height * 0.2 * (i + 1)),
        Offset(size.width, size.height * 0.2 * (i + 1)),
        linePaint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
