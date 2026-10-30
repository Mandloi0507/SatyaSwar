import 'package:flutter/material.dart';

import '../../theme/app_colors.dart';
import '../../theme/app_text_styles.dart';

enum ButtonVariant { primary, secondary, destructive, outlined }

/// Reusable Primary/Secondary/Destructive button component
class PrimaryButton extends StatelessWidget {
  final String label;
  final VoidCallback? onPressed;
  final bool isLoading;
  final IconData? icon;
  final ButtonVariant variant;
  final double height;
  final double? width;

  const PrimaryButton({
    super.key,
    required this.label,
    this.onPressed,
    this.isLoading = false,
    this.icon,
    this.variant = ButtonVariant.primary,
    this.height = 52.0,
    this.width,
  });

  @override
  Widget build(BuildContext context) {
    Color backgroundColor;
    Color foregroundColor;
    BorderSide? borderSide;

    switch (variant) {
      case ButtonVariant.primary:
        backgroundColor = AppColors.primary;
        foregroundColor = Colors.white;
        borderSide = BorderSide.none;
        break;
      case ButtonVariant.secondary:
        backgroundColor = AppColors.surfaceHigh;
        foregroundColor = AppColors.textPrimary;
        borderSide = const BorderSide(color: AppColors.border, width: 1);
        break;
      case ButtonVariant.destructive:
        backgroundColor = AppColors.danger;
        foregroundColor = Colors.white;
        borderSide = BorderSide.none;
        break;
      case ButtonVariant.outlined:
        backgroundColor = Colors.transparent;
        foregroundColor = AppColors.primaryGlow;
        borderSide = const BorderSide(color: AppColors.primary, width: 1.5);
        break;
    }

    final isInteractive = onPressed != null && !isLoading;

    return SizedBox(
      height: height,
      width: width ?? double.infinity,
      child: Material(
        color: isInteractive
            ? backgroundColor
            : backgroundColor.withValues(alpha: 0.4),
        borderRadius: BorderRadius.circular(14),
        child: InkWell(
          onTap: isInteractive ? onPressed : null,
          borderRadius: BorderRadius.circular(14),
          child: Container(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14),
              border: borderSide != BorderSide.none
                  ? Border.fromBorderSide(borderSide)
                  : null,
            ),
            padding: const EdgeInsets.symmetric(horizontal: 20),
            alignment: Alignment.center,
            child: isLoading
                ? SizedBox(
                    width: 22,
                    height: 22,
                    child: CircularProgressIndicator(
                      strokeWidth: 2.5,
                      valueColor: AlwaysStoppedAnimation<Color>(
                        foregroundColor,
                      ),
                    ),
                  )
                : Row(
                    mainAxisSize: MainAxisSize.min,
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      if (icon != null) ...[
                        Icon(icon, size: 20, color: foregroundColor),
                        const SizedBox(width: 8),
                      ],
                      Text(
                        label,
                        style: AppTextStyles.button.copyWith(
                          color: foregroundColor,
                        ),
                      ),
                    ],
                  ),
          ),
        ),
      ),
    );
  }
}
