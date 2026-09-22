import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger" | "outline-danger" | "approve" | "amber";

const variants: Record<Variant, string> = {
  primary: "bg-primary text-white hover:bg-primary-hover border-transparent",
  secondary: "bg-white text-ink border-border hover:bg-canvas",
  ghost: "bg-transparent text-muted border-transparent hover:bg-canvas hover:text-ink",
  danger: "bg-danger text-white hover:bg-red-700 border-transparent",
  "outline-danger": "bg-white text-danger border-danger hover:bg-danger-soft",
  approve: "bg-success text-white hover:bg-green-700 border-transparent",
  amber: "bg-amber text-white hover:bg-amber-600 border-transparent",
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: "sm" | "md";
  children: ReactNode;
}

export function Button({
  variant = "primary",
  size = "md",
  className = "",
  children,
  type = "button",
  ...props
}: ButtonProps) {
  const sizeCls = size === "sm" ? "px-2.5 py-1.5 text-xs" : "px-3.5 py-2 text-sm";
  return (
    <button
      type={type}
      className={`inline-flex items-center justify-center gap-1.5 rounded-md border font-medium transition duration-150 ease-out active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none ${variants[variant]} ${sizeCls} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
