/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
  	container: {
  		center: true,
  		padding: '2rem',
  		screens: {
  			'2xl': '1400px'
  		}
  	},
  	extend: {
  		fontSize: {
  			'ui-2xs': ['var(--text-ui-2xs)', { lineHeight: '1rem' }],
  			'ui-xs': ['var(--text-ui-xs)', { lineHeight: '1.125rem' }],
  			'ui-sm': ['var(--text-ui-sm)', { lineHeight: '1.25rem' }],
  			'ui-base': ['var(--text-ui-base)', { lineHeight: '1.375rem' }],
  			'ui-md': ['var(--text-ui-md)', { lineHeight: '1.5rem' }],
  			'ui-lg': ['var(--text-ui-lg)', { lineHeight: '1.625rem' }],
  			'ui-xl': ['var(--text-ui-xl)', { lineHeight: '1.75rem' }],
  			'ui-2xl': ['var(--text-ui-2xl)', { lineHeight: '2.125rem' }],
  			'ui-3xl': ['var(--text-ui-3xl)', { lineHeight: '2.5rem' }]
  		},
  		spacing: {
  			sidebar: 'var(--layout-sidebar)',
  			'sidebar-collapsed': 'var(--layout-sidebar-collapsed)',
  			topbar: 'var(--layout-topbar)',
  			tabbar: 'var(--layout-tabbar)',
  			'control-sm': 'var(--control-sm)',
  			'control-md': 'var(--control-md)',
  			'control-lg': 'var(--control-lg)'
  		},
  		maxWidth: { form: 'var(--layout-form-max)' },
  		boxShadow: { popover: 'var(--shadow-popover)' },
  		colors: {
  			canvas: 'var(--color-canvas)',
  			surface: {
  				DEFAULT: 'var(--color-surface)',
  				raised: 'var(--color-surface-raised)',
  				sunken: 'var(--color-surface-sunken)',
  				hover: 'var(--color-surface-hover)',
  				active: 'var(--color-surface-active)'
  			},
  			fg: {
  				DEFAULT: 'var(--color-fg)',
  				muted: 'var(--color-fg-muted)',
  				subtle: 'var(--color-fg-subtle)',
  				inverse: 'var(--color-fg-inverse)'
  			},
  			'line-strong': 'var(--color-line-strong)',
  			'line-focus': 'var(--color-line-focus)',
  			action: {
  				DEFAULT: 'var(--color-action)',
  				hover: 'var(--color-action-hover)',
  				active: 'var(--color-action-active)',
  				subtle: 'var(--color-action-subtle)',
  				border: 'var(--color-action-border)'
  			},
  			success: { DEFAULT: 'var(--color-success)', subtle: 'var(--color-success-subtle)', border: 'var(--color-success-border)' },
  			warning: { DEFAULT: 'var(--color-warning)', subtle: 'var(--color-warning-subtle)', border: 'var(--color-warning-border)' },
  			danger: { DEFAULT: 'var(--color-danger)', hover: 'var(--color-danger-hover)', subtle: 'var(--color-danger-subtle)', border: 'var(--color-danger-border)' },
  			info: { DEFAULT: 'var(--color-info)', subtle: 'var(--color-info-subtle)', border: 'var(--color-info-border)' },
  			neutral: { DEFAULT: 'var(--color-neutral)', subtle: 'var(--color-neutral-subtle)', border: 'var(--color-neutral-border)' },
  			positive: 'var(--color-positive)',
  			negative: 'var(--color-negative)',
  			'ui-chart': {
  				'1': 'var(--color-chart-1)', '2': 'var(--color-chart-2)', '3': 'var(--color-chart-3)',
  				'4': 'var(--color-chart-4)', '5': 'var(--color-chart-5)', '6': 'var(--color-chart-6)',
  				grid: 'var(--color-chart-grid)', axis: 'var(--color-chart-axis)'
  			},
  			border: 'hsl(var(--border))',
  			input: 'hsl(var(--input))',
  			ring: 'hsl(var(--ring))',
  			background: 'hsl(var(--background))',
  			foreground: 'hsl(var(--foreground))',
  			primary: {
  				DEFAULT: 'hsl(var(--primary))',
  				foreground: 'hsl(var(--primary-foreground))'
  			},
  			secondary: {
  				DEFAULT: 'hsl(var(--secondary))',
  				foreground: 'hsl(var(--secondary-foreground))'
  			},
  			destructive: {
  				DEFAULT: 'hsl(var(--destructive))',
  				foreground: 'hsl(var(--destructive-foreground))'
  			},
  			muted: {
  				DEFAULT: 'hsl(var(--muted))',
  				foreground: 'hsl(var(--muted-foreground))'
  			},
  			accent: {
  				DEFAULT: 'hsl(var(--accent))',
  				foreground: 'hsl(var(--accent-foreground))'
  			},
  			popover: {
  				DEFAULT: 'hsl(var(--popover))',
  				foreground: 'hsl(var(--popover-foreground))'
  			},
  			card: {
  				DEFAULT: 'hsl(var(--card))',
  				foreground: 'hsl(var(--card-foreground))'
  			},
  			'brand-primary': 'rgb(var(--brand-primary))',
  			'brand-secondary': 'rgb(var(--brand-secondary))',
  			'brand-accent': 'rgb(var(--brand-accent))',
  			'brand-light': 'rgb(var(--brand-light))',
  			chart: {
  				'1': 'hsl(var(--chart-1))',
  				'2': 'hsl(var(--chart-2))',
  				'3': 'hsl(var(--chart-3))',
  				'4': 'hsl(var(--chart-4))',
  				'5': 'hsl(var(--chart-5))'
  			},
  			sidebar: {
  				DEFAULT: 'hsl(var(--sidebar-background))',
  				foreground: 'hsl(var(--sidebar-foreground))',
  				primary: 'hsl(var(--sidebar-primary))',
  				'primary-foreground': 'hsl(var(--sidebar-primary-foreground))',
  				accent: 'hsl(var(--sidebar-accent))',
  				'accent-foreground': 'hsl(var(--sidebar-accent-foreground))',
  				border: 'hsl(var(--sidebar-border))',
  				ring: 'hsl(var(--sidebar-ring))'
  			}
  		},
  		borderRadius: {
  			lg: 'var(--radius)',
  			md: 'calc(var(--radius) - 2px)',
  			sm: 'calc(var(--radius) - 4px)'
  		},
  		keyframes: {
  			'accordion-down': {
  				from: {
  					height: '0'
  				},
  				to: {
  					height: 'var(--radix-accordion-content-height)'
  				}
  			},
  			'accordion-up': {
  				from: {
  					height: 'var(--radix-accordion-content-height)'
  				},
  				to: {
  					height: '0'
  				}
  			}
  		},
  		animation: {
  			'accordion-down': 'accordion-down 0.2s ease-out',
  			'accordion-up': 'accordion-up 0.2s ease-out'
  		}
  	}
  },
	// eslint-disable-next-line @typescript-eslint/no-require-imports
	plugins: [require("tailwindcss-animate")],
};
