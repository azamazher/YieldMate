// ============================================================================
// APP DRAWER - MENU NAVIGATION
// ============================================================================
import 'package:flutter/material.dart';

class AppDrawer extends StatelessWidget {
  final String currentRoute;

  const AppDrawer({
    super.key,
    required this.currentRoute,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Drawer(
      child: ListView(
        padding: EdgeInsets.zero,
        children: [
          // Drawer Header
          DrawerHeader(
            decoration: BoxDecoration(
              color: isDark ? Colors.grey[900] : Colors.green[700],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                Icon(
                  Icons.agriculture,
                  size: 48,
                  color: Colors.white,
                ),
                const SizedBox(height: 8),
                const Text(
                  'YieldMate',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 24,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'Smart Fruit Detection',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.8),
                    fontSize: 14,
                  ),
                ),
              ],
            ),
          ),

          // Home Menu Item
          _buildMenuItem(
            context: context,
            icon: Icons.home,
            title: 'Home',
            route: '/home',
            isSelected: currentRoute == '/home',
            isLocked: false,
          ),

          // Calendar Menu Item
          _buildMenuItem(
            context: context,
            icon: Icons.calendar_today,
            title: 'Calendar',
            route: '/calendar',
            isSelected: currentRoute == '/calendar',
            isLocked: false,
          ),

          const Divider(),

          // Fruit Doctor Menu Item (Locked)
          _buildMenuItem(
            context: context,
            icon: Icons.medical_services,
            title: 'Fruit Doctor',
            route: '/fruit-doctor',
            isSelected: currentRoute == '/fruit-doctor',
            isLocked: true,
          ),

          // Community Menu Item (Locked)
          _buildMenuItem(
            context: context,
            icon: Icons.people,
            title: 'Community',
            route: '/community',
            isSelected: currentRoute == '/community',
            isLocked: true,
          ),

          const Divider(),

          // About Menu Item
          _buildMenuItem(
            context: context,
            icon: Icons.info,
            title: 'About',
            route: '/about',
            isSelected: currentRoute == '/about',
            isLocked: false,
          ),

          const SizedBox(height: 20),
        ],
      ),
    );
  }

  Widget _buildMenuItem({
    required BuildContext context,
    required IconData icon,
    required String title,
    required String route,
    required bool isSelected,
    required bool isLocked,
  }) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return ListTile(
      leading: Icon(
        icon,
        color: isLocked
            ? Colors.grey
            : (isSelected
                ? Colors.green
                : (isDark ? Colors.grey[300] : Colors.grey[700])),
      ),
      title: Row(
        children: [
          Text(
            title,
            style: TextStyle(
              color: isLocked
                  ? Colors.grey
                  : (isDark ? Colors.white : Colors.black87),
              fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
            ),
          ),
          if (isLocked) ...[
            const SizedBox(width: 8),
            Icon(
              Icons.lock,
              size: 16,
              color: Colors.grey,
            ),
          ],
        ],
      ),
      selected: isSelected && !isLocked,
      selectedTileColor: Colors.green.withOpacity(0.1),
      onTap: isLocked
          ? () {
              // Show locked message
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text('$title is coming soon!'),
                  duration: const Duration(seconds: 2),
                ),
              );
            }
          : () {
              Navigator.pop(context); // Close drawer
              if (route != currentRoute) {
                Navigator.pushNamed(context, route);
              }
            },
    );
  }
}

