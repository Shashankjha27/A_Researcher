from app.nli.direction_check import check_direction


def main():
    claim_a = (
        "The treatment significantly improves patient recovery "
        "compared with the control group."
    )

    claim_b = (
        "The treatment does not significantly improve patient "
        "recovery compared with the control group."
    )

    print("Golden Contradiction Demo")
    print("=" * 60)

    print("\nSource A:")
    print(claim_a)

    print("\nSource B:")
    print(claim_b)

    is_contradiction, label, probability = check_direction(
        claim_a,
        claim_b,
    )

    print("\nResult")
    print("-" * 60)
    print(f"Contradiction: {is_contradiction}")
    print(f"NLI label:     {label}")
    print(f"Confidence:    {probability:.4f}")

    if is_contradiction:
        print("\n✅ Correct contradiction detected.")
    else:
        print("\n❌ Contradiction was not detected.")


if __name__ == "__main__":
    main()