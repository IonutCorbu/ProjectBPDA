#![no_std]
use multiversx_sc::imports::*;
use numtoa::NumToA;

#[multiversx_sc::contract]
pub trait AssigningStudents {
    #[init]
    fn init(&self) {
        let caller = self.blockchain().get_caller();
        self.test_results(&caller).set(0);
        self.can_submit(&caller).set(false);
        self.num_tests(&caller).set(0);
    }

    #[storage_mapper("math_tests")]
    fn math_tests(&self, address: &ManagedAddress) -> SingleValueMapper<[[u8; 6]; 5]>;

    #[view]
    #[storage_mapper("test_results")]
    fn test_results(&self, address: &ManagedAddress) -> SingleValueMapper<u64>;

    #[storage_mapper("can_submit")]
    fn can_submit(&self, address: &ManagedAddress) -> SingleValueMapper<bool>;

    #[storage_mapper("num_tests")]
    fn num_tests(&self, address: &ManagedAddress) -> SingleValueMapper<u64>;

    #[endpoint]
    fn generate_test(&self) -> [[u8; 6]; 5] {
        require!(
            self.num_tests(&self.blockchain().get_caller()).get() < 5,
            "You have already generated 5 tests. You finished your homework."
        );
        require!(
            self.can_submit(&self.blockchain().get_caller()).get() == false,
            "You have already generated a test. You can't generate another one until you solve it."
        );
        let mut operations = [[0u8; 6]; 5];

        for i in 0..5 {
            let num1: u8 = self.random_int();
            let num2: u8 = self.random_int();
            let operation_sign: u8 = (self.random_int() as u8 % 4) as u8;

            let mut operation: [u8; 6] = [0u8; 6];

            match operation_sign {
                0 => {
                    let mut string1 = [0u8; 3];
                    num1.numtoa_str(10, &mut string1);

                    let mut string2 = [0u8; 3];
                    num2.numtoa_str(10, &mut string2);

                    operation[0] = string1[2] - 48;
                    operation[1] = b' ';
                    operation[2] = b'+';
                    operation[3] = b' ';
                    operation[4] = string2[2] - 48;
                }
                1 => {
                    let mut string1 = [0u8; 3];
                    num1.numtoa_str(10, &mut string1);

                    let mut string2 = [0u8; 3];
                    num2.numtoa_str(10, &mut string2);

                    operation[0] = string1[2] - 48;
                    operation[1] = b' ';
                    operation[2] = b'-';
                    operation[3] = b' ';
                    operation[4] = string2[2] - 48;
                }
                2 => {
                    // Handle Multiplication
                    let mut string1 = [0u8; 3];
                    num1.numtoa_str(10, &mut string1);

                    let mut string2 = [0u8; 3];
                    num2.numtoa_str(10, &mut string2);

                    operation[0] = string1[2] - 48;
                    operation[1] = b' ';
                    operation[2] = b'*';
                    operation[3] = b' ';
                    operation[4] = string2[2] - 48;
                }
                3 => {
                    let mut string1 = [0u8; 3];
                    num1.numtoa_str(10, &mut string1);

                    let mut string2 = [0u8; 3];
                    let non_zero_num2 = if num2 == 0 { 1 } else { num2 };
                    non_zero_num2.numtoa_str(10, &mut string2);

                    operation[0] = string1[2] - 48;
                    operation[1] = b' ';
                    operation[2] = b'/';
                    operation[3] = b' ';
                    operation[4] = string2[2] - 48;
                }
                _ => {}
            }

            operations[i] = operation;
        }

        let caller = self.blockchain().get_caller();
        self.math_tests(&caller).set(operations);
        self.num_tests(&caller)
            .set(self.num_tests(&caller).get() + 1);
        self.can_submit(&caller).set(true);

        operations
    }

    fn random_int(&self) -> u8 {
        let mut rand_source = RandomnessSource::new();
        let random_value = rand_source.next_u16_in_range(0, 9);
        return random_value as u8;
    }

    #[endpoint]
    fn submit_test(&self, answers: [u8; 6]) -> [[u8; 12]; 5] {
        require!(
            self.can_submit(&self.blockchain().get_caller()).get(),
            "You have already submitted your answers. You can't submit again."
        );
        let caller = self.blockchain().get_caller();
        let test = self.math_tests(&caller).get();

        let mut feedback = [[0u8; 12]; 5];
        let mut score = self.test_results(&caller).get();

        for i in 0..5 {
            let operation = &test[i];

            let mut operation_str_bytes = [0u8; 6];
            let mut idx = 0;

            while operation[idx] != 0 {
                operation_str_bytes[idx] = operation[idx];
                idx += 1;
            }

            let correct_result: i8 = self.solve_operation(&operation_str_bytes);

            let mut feedback_str = [0u8; 12];
            let mut idx = 0;

            let value: i8 = if answers[i] > 127 {
                (answers[i] as i16 - 256) as i8
            } else {
                answers[i] as i8
            };

            if value == correct_result {
                score += 4;
                let correct_msg = "Correct".as_bytes();

                let mut j = 0;
                while j < correct_msg.len() && idx < 12 {
                    feedback_str[idx] = correct_msg[j];
                    idx += 1;
                    j += 1;
                }
            } else {
                let incorrect_msg = "Incorrect".as_bytes();

                let mut j = 0;
                while j < incorrect_msg.len() && idx < 12 {
                    feedback_str[idx] = incorrect_msg[j];
                    idx += 1;
                    j += 1;
                }
            }

            feedback[i] = feedback_str;
        }

        self.test_results(&caller).set(score);
        self.can_submit(&caller).set(false);
        feedback
    }

    fn solve_operation(&self, operation: &[u8; 6]) -> i8 {
        let left: i8;
        let right: i8;
        left = operation[0] as i8;
        right = operation[4] as i8;

        match operation[2] {
            b'+' => left + right as i8,
            b'-' => left - right as i8,
            b'*' => left * right as i8,
            b'/' => {
                if right == 0 {
                    0
                } else {
                    left / right as i8
                }
            }
            _ => 0,
        }
    }
}
