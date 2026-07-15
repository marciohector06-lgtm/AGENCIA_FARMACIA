import { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "danger" | "ghost";

const variantClasses: Record<Variant, string> = {
  primary:
    "bg-red-600 text-white shadow-sm shadow-red-500/20 hover:bg-red-500 focus-visible:outline-red-500",
  secondary:
    "bg-slate-100 text-slate-700 border border-slate-200 hover:bg-slate-200 focus-visible:outline-slate-400",
  danger: "bg-red-800 text-white hover:bg-red-700 focus-visible:outline-red-700",
  ghost: "text-slate-400 hover:bg-slate-100 hover:text-slate-900 focus-visible:outline-slate-500",
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
}

export function Button({ variant = "primary", className = "", ...props }: ButtonProps) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-1.5 rounded-lg px-3.5 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 ${variantClasses[variant]} ${className}`}
      {...props}
    />
  );
}
