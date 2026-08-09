unsigned int integer_mix(long long value, int rounds) {
    unsigned int state = (unsigned int)value;
    int round;
    for (round = 0; round < rounds; ++round) {
        state = state * 1664525u + 1013904223u;
        state ^= state >> 13;
    }
    return state;
}
