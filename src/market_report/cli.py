from __future__ import annotations

import argparse

from market_report.application.pipeline import build_default_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Market Report PPTX")
    parser.add_argument("--config", required=True, help="Path to project config JSON")
    parser.add_argument("--default-config", default="configs/projects/default.json", help="Path to default config JSON")
    parser.add_argument("--run-id", default=None, help="Optional run identifier")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pipeline = build_default_pipeline(args.config)
    result = pipeline.run(args.config, args.default_config, args.run_id)
    
    print(f"\n{'='*60}")
    print(f"Pipeline ejecutado exitosamente")
    print(f"{'='*60}")
    print(f"Run ID: {result.run_id}")
    print(f"Output directory: {result.output_dir}")
    
    if result.consolidated_workbook_path:
        print(f"\n✅ Excel consolidado generado:")
        print(f"   {result.consolidated_workbook_path}")
    
    if result.comparison_summary:
        print(f"\n📊 Comparación con golden:")
        print(f"   ✅ Pestañas OK: {len(result.comparison_summary.get('tabs_ok', []))}")
        print(f"   ⚠️  Pestañas con diferencias: {len(result.comparison_summary.get('tabs_diff', []))}")
        if result.comparison_summary.get('tabs_diff'):
            print(f"   Diferencias en: {', '.join(result.comparison_summary['tabs_diff'][:5])}")
        if result.comparison_summary.get('tabs_missing'):
            print(f"   ⚠️  Pestañas faltantes: {', '.join(result.comparison_summary['tabs_missing'])}")
    
    print(f"\n📁 Archivos generados:")
    print(f"   - PPT: {result.ppt_path}")
    if result.consolidated_workbook_path:
        print(f"   - Excel consolidado: {result.consolidated_workbook_path}")
    print(f"   - CSVs por pestaña: {result.output_dir / 'pipeline_tabs'}")
    print(f"   - Reportes de comparación: {result.output_dir / 'artifacts' / 'diff_reports'}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
